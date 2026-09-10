# ---------------------------------------------------------------------------
# openai.py — OpenAI provider adapter
# ---------------------------------------------------------------------------
# Wraps the official ``openai`` Python SDK behind the BaseProvider
# interface so the router can treat OpenAI models uniformly.
# ---------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import Any

from openai import AsyncOpenAI

from app.config.settings import get_settings
from app.models.providers.base import BaseProvider, ProviderResponse

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseProvider):
    """Concrete adapter for the OpenAI API."""

    provider_name = "openai"

    def __init__(self) -> None:
        settings = get_settings()
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def complete(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> ProviderResponse:
        """Call the OpenAI chat-completion endpoint."""
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens

        response = await self._client.chat.completions.create(**kwargs)

        choice = response.choices[0]
        usage = response.usage

        return ProviderResponse(
            content=choice.message.content or "",
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
            model=response.model,
            raw=response.model_dump(),
        )

    async def health_check(self) -> bool:
        """Hit the models endpoint to verify the API key is valid."""
        try:
            await self._client.models.list()
            return True
        except Exception as exc:
            logger.warning("OpenAI health check failed: %s", exc)
            return False

    def count_tokens(self, text: str, model: str) -> int:
        """Rough heuristic: ~4 chars per token.

        The official tiktoken library could be used for exact counts but
        adds a dependency; this approximation is sufficient for the cost
        estimation done in Phase 6.
        """
        return max(1, len(text) // 4)
