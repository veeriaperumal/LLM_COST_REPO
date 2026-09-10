# ---------------------------------------------------------------------------
# schemas.py — Pydantic data models for the model abstraction layer
# ---------------------------------------------------------------------------
# These schemas define the shape of model metadata, pricing, and
# capability information stored in the ModelRegistry.
# ---------------------------------------------------------------------------

from enum import Enum

from pydantic import BaseModel, Field


class TaskType(str, Enum):
    """Supported LLM task types (from spec line 20)."""
    classification = "classification"
    extraction = "extraction"
    summarisation = "summarisation"
    qa = "qa"


class PricingInfo(BaseModel):
    """Cost per 1 000 tokens in USD for a single model."""

    input_per_1k: float = Field(
        ..., ge=0, description="USD cost per 1 000 input tokens"
    )
    output_per_1k: float = Field(
        ..., ge=0, description="USD cost per 1 000 output tokens"
    )

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Return the total USD cost for a given token usage."""
        return (
            input_tokens / 1000 * self.input_per_1k
            + output_tokens / 1000 * self.output_per_1k
        )


class CapabilitySet(BaseModel):
    """What a model can and cannot do."""

    supported_tasks: list[TaskType] = Field(
        default_factory=list,
        description="Task types this model handles",
    )
    supports_structured_output: bool = False
    supports_tools: bool = False
    max_context_tokens: int = Field(
        default=4096, ge=1, description="Context-window size in tokens"
    )


class ModelMetadata(BaseModel):
    """Full descriptor for a single LLM available to the router."""

    model_id: str = Field(
        ..., description="Unique identifier, e.g. 'gpt-4o' or 'claude-3-5-sonnet'"
    )
    provider: str = Field(
        ..., description="Provider name: 'openai', 'anthropic', etc."
    )
    capabilities: CapabilitySet = Field(default_factory=CapabilitySet)
    pricing: PricingInfo = Field(
        default_factory=lambda: PricingInfo(input_per_1k=0.0, output_per_1k=0.0)
    )
    quality_score: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Normalized quality score 0-1 (populated by Phase 11 feedback)",
    )
    typical_latency_ms: float = Field(
        default=0.0, ge=0.0,
        description="Typical end-to-end latency in milliseconds",
    )
