# ---------------------------------------------------------------------------
# catalog.py — Default model catalog
# ---------------------------------------------------------------------------
# Seeds a ModelRegistry with a representative set of production models so
# the gateway can route out of the box.  Quality scores default to 0.0
# (Phase 11 will fill them from historical feedback).  Latencies and prices
# are indicative values published by the providers.
# ---------------------------------------------------------------------------

from app.models.registry import ModelRegistry
from app.models.schemas import (
    CapabilitySet,
    ModelMetadata,
    PricingInfo,
    TaskType,
)


def build_default_registry() -> ModelRegistry:
    """Build and return the seed ModelRegistry."""
    registry = ModelRegistry()

    registry.register(
        ModelMetadata(
            model_id="gpt-4o",
            provider="openai",
            capabilities=CapabilitySet(
                supported_tasks=[
                    TaskType.classification,
                    TaskType.extraction,
                    TaskType.summarisation,
                    TaskType.qa,
                ],
                supports_structured_output=True,
                supports_tools=True,
                max_context_tokens=128_000,
            ),
            pricing=PricingInfo(input_per_1k=0.0025, output_per_1k=0.010),
            typical_latency_ms=800.0,
        )
    )

    registry.register(
        ModelMetadata(
            model_id="gpt-4o-mini",
            provider="openai",
            capabilities=CapabilitySet(
                supported_tasks=[
                    TaskType.classification,
                    TaskType.qa,
                ],
                supports_structured_output=True,
                supports_tools=False,
                max_context_tokens=128_000,
            ),
            pricing=PricingInfo(input_per_1k=0.00015, output_per_1k=0.0006),
            typical_latency_ms=400.0,
        )
    )

    registry.register(
        ModelMetadata(
            model_id="claude-3-5-sonnet",
            provider="anthropic",
            capabilities=CapabilitySet(
                supported_tasks=[
                    TaskType.classification,
                    TaskType.extraction,
                    TaskType.summarisation,
                    TaskType.qa,
                ],
                supports_structured_output=True,
                supports_tools=True,
                max_context_tokens=200_000,
            ),
            pricing=PricingInfo(input_per_1k=0.003, output_per_1k=0.015),
            typical_latency_ms=1200.0,
        )
    )

    registry.register(
        ModelMetadata(
            model_id="claude-haiku-4-5",
            provider="anthropic",
            capabilities=CapabilitySet(
                supported_tasks=[TaskType.classification],
                supports_structured_output=False,
                supports_tools=False,
                max_context_tokens=200_000,
            ),
            pricing=PricingInfo(input_per_1k=0.0008, output_per_1k=0.004),
            typical_latency_ms=350.0,
        )
    )

    return registry