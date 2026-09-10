# ---------------------------------------------------------------------------
# test_registry.py — Tests for ModelRegistry
# ---------------------------------------------------------------------------

import pytest

from app.models.registry import ModelRegistry
from app.models.schemas import (
    CapabilitySet,
    ModelMetadata,
    PricingInfo,
    TaskType,
)


# -- Fixtures ---------------------------------------------------------------

def _gpt4o() -> ModelMetadata:
    return ModelMetadata(
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
        pricing=PricingInfo(input_per_1k=0.0025, output_per_1k=0.01),
    )


def _gpt4o_mini() -> ModelMetadata:
    return ModelMetadata(
        model_id="gpt-4o-mini",
        provider="openai",
        capabilities=CapabilitySet(
            supported_tasks=[TaskType.classification, TaskType.qa],
            supports_structured_output=True,
            supports_tools=False,
            max_context_tokens=128_000,
        ),
        pricing=PricingInfo(input_per_1k=0.00015, output_per_1k=0.0006),
    )


def _claude_sonnet() -> ModelMetadata:
    return ModelMetadata(
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
    )


def _claude_haiku() -> ModelMetadata:
    return ModelMetadata(
        model_id="claude-haiku-4-5",
        provider="anthropic",
        capabilities=CapabilitySet(
            supported_tasks=[TaskType.classification],
            supports_structured_output=False,
            supports_tools=False,
            max_context_tokens=200_000,
        ),
        pricing=PricingInfo(input_per_1k=0.0008, output_per_1k=0.004),
    )


@pytest.fixture
def registry() -> ModelRegistry:
    """Pre-populated registry with 4 models."""
    reg = ModelRegistry()
    for m in [_gpt4o(), _gpt4o_mini(), _claude_sonnet(), _claude_haiku()]:
        reg.register(m)
    return reg


# -- Register / unregister --------------------------------------------------

def test_register_and_get():
    """register + get round-trip."""
    reg = ModelRegistry()
    reg.register(_gpt4o())
    assert reg.get("gpt-4o") is not None
    assert reg.get("gpt-4o").provider == "openai"


def test_register_overwrites():
    """Registering the same model_id replaces the previous entry."""
    reg = ModelRegistry()
    m1 = ModelMetadata(model_id="x", provider="a", quality_score=0.1)
    m2 = ModelMetadata(model_id="x", provider="b", quality_score=0.9)
    reg.register(m1)
    reg.register(m2)
    assert reg.get("x").provider == "b"
    assert len(reg) == 1


def test_unregister_existing():
    """unregister removes the model and returns True."""
    reg = ModelRegistry()
    reg.register(_gpt4o())
    assert reg.unregister("gpt-4o") is True
    assert reg.get("gpt-4o") is None


def test_unregister_nonexistent():
    """unregister returns False for unknown IDs."""
    reg = ModelRegistry()
    assert reg.unregister("nope") is False


# -- Read operations --------------------------------------------------------

def test_get_all(registry):
    """get_all returns every registered model."""
    assert len(registry.get_all()) == 4


def test_get_by_provider_openai(registry):
    """get_by_provider filters correctly for openai."""
    openai_models = registry.get_by_provider("openai")
    assert len(openai_models) == 2
    ids = {m.model_id for m in openai_models}
    assert ids == {"gpt-4o", "gpt-4o-mini"}


def test_get_by_provider_anthropic(registry):
    """get_by_provider filters correctly for anthropic."""
    anthropic_models = registry.get_by_provider("anthropic")
    assert len(anthropic_models) == 2


def test_get_by_provider_empty():
    """get_by_provider returns empty list for unknown provider."""
    registry = ModelRegistry()
    registry.register(_gpt4o())
    assert registry.get_by_provider("cohere") == []


# -- filter_by_task ---------------------------------------------------------

def test_filter_by_task_classification(registry):
    """All 4 models support classification."""
    result = registry.filter_by_task(TaskType.classification)
    assert len(result) == 4


def test_filter_by_task_extraction(registry):
    """Only gpt-4o and claude-sonnet support extraction."""
    result = registry.filter_by_task(TaskType.extraction)
    ids = {m.model_id for m in result}
    assert ids == {"gpt-4o", "claude-3-5-sonnet"}


def test_filter_by_task_summarisation(registry):
    """Only gpt-4o and claude-sonnet support summarisation."""
    result = registry.filter_by_task(TaskType.summarisation)
    assert len(result) == 2


def test_filter_by_task_qa(registry):
    """gpt-4o, gpt-4o-mini, and claude-sonnet support qa."""
    result = registry.filter_by_task(TaskType.qa)
    assert len(result) == 3


# -- filter_by_capability ---------------------------------------------------

def test_filter_structured_output(registry):
    """3 models support structured output (not haiku)."""
    result = registry.filter_by_capability(require_structured_output=True)
    assert len(result) == 3
    ids = {m.model_id for m in result}
    assert "claude-haiku-4-5" not in ids


def test_filter_tools(registry):
    """Only 2 models support tools."""
    result = registry.filter_by_capability(require_tools=True)
    assert len(result) == 2


def test_filter_min_context(registry):
    """Filtering by 150k context removes gpt-4o and gpt-4o-mini (128k)."""
    result = registry.filter_by_capability(min_context_tokens=150_000)
    assert len(result) == 2
    ids = {m.model_id for m in result}
    assert ids == {"claude-3-5-sonnet", "claude-haiku-4-5"}


def test_filter_combined(registry):
    """require_tools + min_context_tokens=200_000 leaves only claude-sonnet."""
    result = registry.filter_by_capability(
        require_tools=True, min_context_tokens=200_000
    )
    assert len(result) == 1
    assert result[0].model_id == "claude-3-5-sonnet"


def test_filter_no_constraints(registry):
    """No constraints returns all models."""
    result = registry.filter_by_capability()
    assert len(result) == 4


# -- __len__ ----------------------------------------------------------------

def test_len(registry):
    """len(registry) returns the model count."""
    assert len(registry) == 4


def test_len_empty():
    """Empty registry has length 0."""
    assert len(ModelRegistry()) == 0
