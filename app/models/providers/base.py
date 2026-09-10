# ---------------------------------------------------------------------------
# base.py — Abstract base class for LLM provider adapters
# ---------------------------------------------------------------------------
# Every concrete provider (OpenAI, Anthropic, …) implements this interface
# so the router can call any provider through a uniform API.
# ---------------------------------------------------------------------------

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class ProviderResponse(BaseModel):
    """Normalized response returned by every provider adapter."""

    content: str
    input_tokens: int
    output_tokens: int
    model: str
    raw: dict[str, Any] | None = None


class BaseProvider(ABC):
    """Interface that all provider adapters must implement."""

    provider_name: str

    @abstractmethod
    async def complete(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> ProviderResponse:
        """Send a chat-completion request and return a normalized response."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if the provider API is reachable."""
        ...

    @abstractmethod
    def count_tokens(self, text: str, model: str) -> int:
        """Estimate the token count for *text* under the given model."""
        ...
