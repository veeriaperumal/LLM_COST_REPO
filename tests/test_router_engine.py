# ---------------------------------------------------------------------------
# test_router_engine.py — End-to-end tests for RouterEngine
# ---------------------------------------------------------------------------
# Uses a hand-built registry where the expected winner is computable from
# the documented scoring formula.
# ---------------------------------------------------------------------------

import pytest

from app.models.registry import ModelRegistry
from app.models.schemas import (
    CapabilitySet,
    ModelMetadata,
    PricingInfo,
    TaskType,
)
from app.router.engine import RouterEngine, RoutingError, default_engine
from app.router.schemas import RoutingRequest


ALL_TASKS = [
    TaskType.classification,
    TaskType.extraction,
    TaskType.summarisation,
    TaskType.qa,
]


def _model(
    model_id: str,
    quality: float,
    latency_ms: float,
    in_per_1k: float,
    out_per_1k: float,
    *,
    tasks=None,
    structured: bool = False,
    tools: bool = False,
    context: int = 128_000,
) -> ModelMetadata:
    return ModelMetadata(
        model_id=model_id,
        provider="test",
        capabilities=CapabilitySet(
            supported_tasks=tasks or [TaskType.classification],
            supports_structured_output=structured,
            supports_tools=tools,
            max_context_tokens=context,
        ),
        pricing=PricingInfo(input_per_1k=in_per_1k, output_per_1k=out_per_1k),
        quality_score=quality,
        typical_latency_ms=latency_ms,
    )


@pytest.fixture
def registry() -> ModelRegistry:
    """Four models with distinct trade-offs.

    - premium:  best quality, slowest, most expensive
    - balanced: middle everywhere
    - cheap:    lowest quality, fastest, cheapest (classification & qa only)
    - dominated: worse than **balanced** on every axis → Pareto-removed
    """
    reg = ModelRegistry()
    reg.register(
        _model(
            "premium", 0.98, 900, 0.010, 0.030,
            tasks=ALL_TASKS, structured=True, tools=True,
        )
    )
    reg.register(
        _model(
            "balanced", 0.90, 500, 0.005, 0.015,
            tasks=ALL_TASKS, structured=True, tools=True,
        )
    )
    reg.register(
        _model(
            "cheap", 0.55, 200, 0.0001, 0.0004,
            tasks=[TaskType.classification, TaskType.qa],
            structured=False, tools=False, context=64_000,
        )
    )
    reg.register(
        _model(
            "dominated", 0.85, 700, 0.006, 0.018,
            tasks=ALL_TASKS, structured=True, tools=True,
        )
    )
    return reg


def _request(**kw) -> RoutingRequest:
    """Convenience builder defaulting to a classification request with
    1000 input / 256 output tokens."""
    defaults = {
        "task": TaskType.classification,
        "prompt": "x" * 256,  # fallback heuristic irrelevant; explicit tokens
        "estimated_input_tokens": 1000,
        "estimated_output_tokens": 256,
    }
    defaults.update(kw)
    return RoutingRequest(**defaults)


# -- Capability filtering --------------------------------------------------

def test_capability_filter_excludes_incapable(registry):
    """summarisation excludes 'cheap' (classification/qa only)."""
    result = RouterEngine(registry).route(_request(task=TaskType.summarisation))
    assert result.eligible == ["premium", "balanced", "dominated"]
    stage_ids = {e.model_id for e in result.exclusions if e.stage == "capability"}
    assert stage_ids == {"cheap"}


def test_structured_output_filter(registry):
    """Requiring structured output excludes 'cheap'."""
    result = RouterEngine(registry).route(
        _request(require_structured_output=True)
    )
    assert "cheap" not in result.eligible
    cheap_excl = [
        e for e in result.exclusions
        if e.model_id == "cheap" and e.stage == "capability"
    ]
    assert cheap_excl and "structured" in cheap_excl[0].reason


def test_tools_filter(registry):
    """Requiring tool-calling excludes 'cheap'."""
    result = RouterEngine(registry).route(_request(require_tools=True))
    assert "cheap" not in result.eligible
    assert any(e.stage == "capability" for e in result.exclusions)


def test_min_context_filter(registry):
    """Requiring a large context excludes 'cheap' (64k < 100k)."""
    result = RouterEngine(registry).route(_request(min_context_tokens=100_000))
    assert "cheap" not in result.eligible
    reason = next(
        e.reason for e in result.exclusions
        if e.model_id == "cheap" and e.stage == "capability"
    )
    assert "context" in reason


# -- Budget / health constraints -------------------------------------------

def test_budget_constraint(registry):
    """max_cost_usd removes models whose estimated cost exceeds the budget."""
    # premium 0.01768, balanced 0.00884, dominated 0.010608 all > 0.003;
    # cheap 0.0002024 stays.
    result = RouterEngine(registry).route(_request(max_cost_usd=0.003))
    assert "premium" not in result.eligible or any(
        e.model_id == "premium" and e.stage == "budget" for e in result.exclusions
    )
    assert result.selected_model == "cheap"


def test_health_constraint_unavailable(registry):
    """unavailable_models removes the listed model."""
    result = RouterEngine(registry).route(_request(unavailable_models={"premium"}))
    assert any(
        e.model_id == "premium" and e.stage == "health" for e in result.exclusions
    )
    assert "premium" not in result.pareto_frontier


# -- Pareto + scoring + selection ------------------------------------------

def test_pareto_removes_dominated(registry):
    """Balanced dominates 'dominated' on all axes → removed."""
    result = RouterEngine(registry).route(_request())
    assert "dominated" not in result.pareto_frontier
    assert any(e.model_id == "dominated" and e.stage == "pareto"
               for e in result.exclusions)


def test_selection_and_score_board(registry):
    """cheap wins the default request; scores exist only for the frontier."""
    result = RouterEngine(registry).route(_request())
    assert result.selected_model == "cheap"
    assert set(result.scores.keys()) == {"premium", "balanced", "cheap"}
    # Sanity: cheap has the best latency & cost scores
    assert result.scores["cheap"].latency_score == 1.0
    assert result.scores["cheap"].cost_score == 1.0


def test_balanced_wins_when_cheap_ineligible(registry):
    """With cheap filtered out by context, balanced beats premium."""
    result = RouterEngine(registry).route(_request(min_context_tokens=100_000))
    assert result.selected_model == "balanced"
    assert set(result.pareto_frontier) == {"premium", "balanced"}


# -- Decision log ----------------------------------------------------------

def test_decision_log_contains_all_stages(registry):
    """The decision log must cover capability, pareto, and score stages."""
    result = RouterEngine(registry).route(_request())
    stages = {entry["stage"] for entry in result.decision_log}
    assert {"capability", "pareto", "score"} <= stages
    # Score entry carries the selected model
    score_entries = [
        e for e in result.decision_log if e["stage"] == "score"
    ]
    assert score_entries and score_entries[-1]["detail"]["selected"] == "cheap"


# -- Error paths -----------------------------------------------------------

def test_no_eligible_models_raises(registry):
    """A task no registered model supports must raise RoutingError."""
    bad_registry = ModelRegistry()
    bad_registry.register(
        _model("only-class", 0.9, 300, 0.001, 0.002)
    )
    engine = RouterEngine(bad_registry)
    req = _request(task=TaskType.summarisation)
    with pytest.raises(RoutingError) as exc_info:
        engine.route(req)
    assert "No eligible models" in str(exc_info.value)


def test_empty_registry_raises():
    """An empty registry must raise RoutingError."""
    engine = RouterEngine(ModelRegistry())
    with pytest.raises(RoutingError) as exc_info:
        engine.route(_request())
    assert "No models registered" in str(exc_info.value)


def test_all_rejected_by_budget_raises(registry):
    """When every eligible model exceeds the budget, raise."""
    engine = RouterEngine(registry)
    with pytest.raises(RoutingError) as exc_info:
        engine.route(_request(max_cost_usd=0.0001))
    assert "rejected by constraints" in str(exc_info.value)


# -- Edge cases ------------------------------------------------------------

def test_single_candidate_still_routed():
    """A lone eligible model is routed (normalized to 1.0)."""
    reg = ModelRegistry()
    reg.register(_model("solo", 0.9, 400, 0.001, 0.002))
    result = RouterEngine(reg).route(_request())
    assert result.selected_model == "solo"
    assert result.pareto_frontier == ["solo"]


def test_token_heuristic_fallback(registry):
    """Without estimated_input_tokens the engine falls back to len//4."""
    result = RouterEngine(registry).route(
        _request(estimated_input_tokens=None)
    )
    # Route must still succeed and pick a model
    assert result.selected_model is not None


def test_default_catalog_engine_routes():
    """The seed catalog produces a routing decision out of the box."""
    engine = default_engine()
    result = engine.route(
        RoutingRequest(task=TaskType.classification, prompt="Is this spam?")
    )
    assert result.selected_model is not None
    assert result.decision_log  # non-empty