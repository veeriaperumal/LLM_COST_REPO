# ---------------------------------------------------------------------------
# anthropic.py — Anthropic provider adapter
# ---------------------------------------------------------------------------
# Wraps the official ``anthropic`` Python SDK behind the BaseProvider
# interface so the router can treat Anthropic models uniformly.
# ---------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import Any

import anthropic

from app.config.settings import get_settings
from app.models.providers.base import BaseProvider, ProviderResponse

logger = logging.getLogger(__name__)


class AnthropicProvider(BaseProvider):
    """Concrete adapter for the Anthropic (Claude) API."""

    provider_name = "anthropic"

    def __init__(self) -> None:
        settings = get_settings()
        self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def complete(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> ProviderResponse:
        """Call the Anthropic messages endpoint.

        Anthropic requires a ``system`` kwarg rather than a system message
        in the messages list.  If the first message has role ``system`` we
        extract it; otherwise an empty system prompt is used.
        """
        system_prompt = ""
        user_messages = messages

        if messages and messages[0].get("role") == "system":
            system_prompt = messages[0]["content"]
            user_messages = messages[1:]

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": user_messages,
            "temperature": temperature,
            "max_tokens": max_tokens or 4096,
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        response = await self._client.messages.create(**kwargs)

        # Extract text content from the response blocks
        content_text = ""
        for block in response.content:
            if block.type == "text":
                content_text += block.text

        return ProviderResponse(
            content=content_text,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            model=response.model,
            raw=response.model_dump(),
        )

    async def health_check(self) -> bool:
        """Send a minimal request to verify the API key works."""
        try:
            await self._client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1,
                messages=[{"role": "user", "content": "ping"}],
            )
            return True
        except Exception as exc:
            logger.warning("Anthropic health check failed: %s", exc)
            return False

    def count_tokens(self, text: str, model: str) -> int:
        """Rough heuristic: ~4 chars per token.

        Anthropic's tokenizers vary by model version; this approximation
        is acceptable for Phase 0-1 cost estimation.
        """
        return max(1, len(text) // 4)
