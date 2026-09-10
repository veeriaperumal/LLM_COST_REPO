# ---------------------------------------------------------------------------
# test_schemas.py — Tests for Pydantic data models in app.models.schemas
# ---------------------------------------------------------------------------

import pytest

from app.models.schemas import (
    CapabilitySet,
    ModelMetadata,
    PricingInfo,
    TaskType,
)


# -- TaskType enum ----------------------------------------------------------

def test_task_type_values():
    """TaskType members must match the spec task types."""
    assert TaskType.classification.value == "classification"
    assert TaskType.extraction.value == "extraction"
    assert TaskType.summarisation.value == "summarisation"
    assert TaskType.qa.value == "qa"


def test_task_type_count():
    """Exactly four task types are supported."""
    assert len(TaskType) == 4


# -- PricingInfo ------------------------------------------------------------

def test_pricing_info_calculation():
    """calculate_cost should return the correct USD amount."""
    p = PricingInfo(input_per_1k=0.005, output_per_1k=0.015)
    cost = p.calculate_cost(input_tokens=1000, output_tokens=2000)
    # 1000 * 0.005/1000 + 2000 * 0.015/1000 = 0.005 + 0.030 = 0.035
    assert cost == pytest.approx(0.035)


def test_pricing_info_zero_tokens():
    """Zero tokens should produce zero cost."""
    p = PricingInfo(input_per_1k=0.01, output_per_1k=0.02)
    assert p.calculate_cost(0, 0) == 0.0


def test_pricing_info_rejects_negative():
    """Negative per-1k costs should fail validation."""
    with pytest.raises(Exception):
        PricingInfo(input_per_1k=-0.01, output_per_1k=0.01)


# -- CapabilitySet ----------------------------------------------------------

def test_capability_set_defaults():
    """Defaults: no tasks, no structured output, no tools, 4096 context."""
    c = CapabilitySet()
    assert c.supported_tasks == []
    assert c.supports_structured_output is False
    assert c.supports_tools is False
    assert c.max_context_tokens == 4096


def test_capability_set_custom():
    """Custom values are stored correctly."""
    c = CapabilitySet(
        supported_tasks=[TaskType.classification, TaskType.qa],
        supports_structured_output=True,
        supports_tools=True,
        max_context_tokens=128_000,
    )
    assert TaskType.classification in c.supported_tasks
    assert TaskType.qa in c.supported_tasks
    assert c.supports_structured_output is True
    assert c.max_context_tokens == 128_000


def test_capability_set_rejects_zero_context():
    """max_context_tokens must be >= 1."""
    with pytest.raises(Exception):
        CapabilitySet(max_context_tokens=0)


# -- ModelMetadata ----------------------------------------------------------

def test_model_metadata_minimal():
    """Only model_id and provider are required; everything else has defaults."""
    m = ModelMetadata(model_id="gpt-4o", provider="openai")
    assert m.model_id == "gpt-4o"
    assert m.provider == "openai"
    assert m.quality_score == 0.0
    assert m.typical_latency_ms == 0.0
    assert m.capabilities.supported_tasks == []


def test_model_metadata_full():
    """All fields are stored correctly."""
    m = ModelMetadata(
        model_id="claude-3-5-sonnet",
        provider="anthropic",
        capabilities=CapabilitySet(
            supported_tasks=[TaskType.classification],
            max_context_tokens=200_000,
        ),
        pricing=PricingInfo(input_per_1k=0.003, output_per_1k=0.015),
        quality_score=0.85,
        typical_latency_ms=1200.0,
    )
    assert m.quality_score == 0.85
    assert m.pricing.input_per_1k == 0.003
    assert m.capabilities.max_context_tokens == 200_000


def test_model_metadata_rejects_quality_out_of_range():
    """quality_score must be between 0.0 and 1.0."""
    with pytest.raises(Exception):
        ModelMetadata(
            model_id="bad", provider="x", quality_score=1.5
        )
