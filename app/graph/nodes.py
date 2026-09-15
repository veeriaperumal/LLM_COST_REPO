# ---------------------------------------------------------------------------
# nodes.py — Node functions for the LangGraph state machine
# ---------------------------------------------------------------------------
# Each node reads the current GraphState, performs one stage of the spec
# workflow, and returns a partial dict to merge into the state.
#
# Spec routing method (spec.md:84-98):
#   4. Analyse task
#   5. Determine tool/context/structured-output requirements
#   6. Filter incapable models
#   7. Apply budget and provider-health constraints
#  11. Execute
#  12. Evaluate response
#  13. Accept, revise, or escalate
# ---------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import Any

from app.models.providers.base import ProviderResponse
from app.models.registry import ModelRegistry
from app.router.engine import RouterEngine, RoutingError
from app.router.schemas import RoutingRequest, RoutingResult

logger = logging.getLogger("app.graph")


def _build_registry() -> ModelRegistry:
    """Build the default registry (lazy import to avoid circular deps)."""
    from app.models.catalog import build_default_registry
    return build_default_registry()


def _get_provider(model_provider: str):
    """Instantiate the provider adapter by name."""
    if model_provider == "openai":
        from app.models.providers.openai import OpenAIProvider
        return OpenAIProvider()
    elif model_provider == "anthropic":
        from app.models.providers.anthropic import AnthropicProvider
        return AnthropicProvider()
    raise ValueError(f"Unknown provider: {model_provider}")


# -- Node: analyze -------------------------------------------------------------

def analyze_node(state: GraphState) -> dict[str, Any]:
    """Stage 4-5: Analyse the task and extract requirements.

    Records which stages have completed and initialises retry counters.
    """
    logger.info("graph[analyze] task analysis started")

    request = RoutingRequest(**state["request"])

    stages = list(state.get("stages_completed", []))
    stages.append("analyze")

    return {
        "stages_completed": stages,
        "retry_count": state.get("retry_count", 0),
        "max_retries": state.get("max_retries", 2),
        "unavailable_models": list(state.get("unavailable_models", [])),
    }


# -- Node: filter --------------------------------------------------------------

def filter_node(state: GraphState) -> dict[str, Any]:
    """Stage 6-7: Run capability + constraint filtering via RouterEngine.

    This performs the same filtering the RouterEngine does internally, but
    we surface the intermediate RoutingResult so later nodes can inspect it.
    """
    logger.info("graph[filter] capability + constraint filtering")
    request = RoutingRequest(**state["request"])
    engine = RouterEngine(_build_registry())

    # Merge any previously excluded models into the request
    excluded = set(state.get("unavailable_models", []))
    if excluded:
        request = request.model_copy(update={"unavailable_models": excluded})

    try:
        result = engine.route(request)
    except RoutingError as exc:
        return {
            "routing_result": None,
            "error": exc.message,
            "selected_model": None,
        }

    stages = list(state.get("stages_completed", []))
    stages.append("filter")

    return {
        "routing_result": result.model_dump(),
        "selected_model": result.selected_model,
        "error": None,
        "stages_completed": stages,
    }


# -- Node: route ---------------------------------------------------------------

def route_node(state: GraphState) -> dict[str, Any]:
    """Stage 10 (re-entry point for revise): confirm or re-run model selection.

    If coming from the revise path this node re-runs the full routing
    pipeline excluding previously-failed models.
    """
    logger.info("graph[route] model selection (retry=%d)", state.get("retry_count", 0))
    request = RoutingRequest(**state["request"])
    engine = RouterEngine(_build_registry())

    excluded = set(state.get("unavailable_models", []))
    if excluded:
        request = request.model_copy(update={"unavailable_models": excluded})

    try:
        result = engine.route(request)
    except RoutingError as exc:
        return {
            "routing_result": None,
            "error": exc.message,
            "selected_model": None,
        }

    stages = list(state.get("stages_completed", []))
    if "route" not in stages:
        stages.append("route")

    return {
        "routing_result": result.model_dump(),
        "selected_model": result.selected_model,
        "error": None,
        "stages_completed": stages,
    }


# -- Node: execute -------------------------------------------------------------

def execute_node(state: GraphState) -> dict[str, Any]:
    """Stage 11: Call the selected model's provider adapter.

    Uses a synchronous wrapper around the async provider call so the
    node works with both ``graph.invoke()`` and ``graph.ainvoke()``.
    """
    import asyncio

    selected = state.get("selected_model")
    if not selected:
        return {
            "error": "No model selected for execution",
            "provider_response": None,
        }

    logger.info("graph[execute] calling model %s", selected)

    # Find the provider name from the routing result
    routing_result = state.get("routing_result")
    provider_name = None
    if routing_result:
        registry = _build_registry()
        model = registry.get(selected)
        if model:
            provider_name = model.provider

    if not provider_name:
        return {
            "error": f"Cannot determine provider for model '{selected}'",
            "provider_response": None,
        }

    try:
        provider = _get_provider(provider_name)
        request = RoutingRequest(**state["request"])
        messages = [{"role": "user", "content": request.prompt}]

        async def _call():
            return await provider.complete(
                model=selected,
                messages=messages,
                max_tokens=request.estimated_output_tokens,
            )

        # Run the async provider call; reuse existing loop if available
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                response = pool.submit(asyncio.run, _call()).result()
        else:
            response = asyncio.run(_call())

        stages = list(state.get("stages_completed", []))
        stages.append("execute")

        return {
            "provider_response": response.model_dump(),
            "error": None,
            "stages_completed": stages,
        }
    except Exception as exc:
        logger.warning("graph[execute] provider error: %s", exc)
        return {
            "error": f"Execution failed: {exc}",
            "provider_response": None,
        }


# -- Node: evaluate ------------------------------------------------------------

def evaluate_node(state: GraphState) -> dict[str, Any]:
    """Stage 12: Heuristic evaluation of the provider response.

    Heuristics (MVP):
      - Response exists and has non-empty content → base score 0.6
      - Content length > 50 chars → +0.1
      - Content length > 200 chars → +0.1
      - No error markers ("error", "failed", "sorry") → +0.1
      - Content not a refusal ("i cannot", "i'm unable") → +0.1
      - Total capped at 1.0
    """
    logger.info("graph[evaluate] heuristic evaluation")
    response_dict = state.get("provider_response")
    if not response_dict:
        return {
            "evaluation": {"score": 0.0, "status": "escalate", "reason": "no response"},
        }

    content = response_dict.get("content", "")

    score = 0.0
    reasons: list[str] = []

    # Base: response exists
    if content:
        score += 0.6
        reasons.append("response present")
    else:
        reasons.append("empty response")
        return {
            "evaluation": {"score": 0.0, "status": "escalate", "reason": "; ".join(reasons)},
        }

    # Length bonuses
    if len(content) > 50:
        score += 0.1
        reasons.append("adequate length")
    if len(content) > 200:
        score += 0.1
        reasons.append("substantial length")

    # No error markers
    error_markers = ["error", "failed", "sorry", "unable"]
    content_lower = content.lower()
    if not any(m in content_lower for m in error_markers):
        score += 0.1
        reasons.append("no error markers")

    # Not a refusal
    refusals = ["i cannot", "i can't", "i'm unable", "i am unable"]
    if not any(r in content_lower for r in refusals):
        score += 0.1
        reasons.append("not a refusal")

    score = min(score, 1.0)

    # Decision
    if score >= 0.8:
        status = "accept"
    elif score >= 0.5 and state.get("retry_count", 0) < state.get("max_retries", 2):
        status = "revise"
    else:
        status = "escalate"

    stages = list(state.get("stages_completed", []))
    stages.append("evaluate")

    return {
        "evaluation": {"score": round(score, 2), "status": status, "reason": "; ".join(reasons)},
        "stages_completed": stages,
    }


# -- Node: finalize ------------------------------------------------------------

def finalize_node(state: GraphState) -> dict[str, Any]:
    """Stage 13+: Package the final result for the API response."""
    logger.info("graph[finalize] assembling result")

    request = RoutingRequest(**state["request"])
    evaluation = state.get("evaluation", {})
    response_dict = state.get("provider_response")
    routing_dict = state.get("routing_result")

    # Compute cost estimate
    cost_usd = 0.0
    if routing_dict and state.get("selected_model"):
        scores = routing_dict.get("scores", {})
        selected = state["selected_model"]
        if selected in scores:
            cost_usd = scores[selected].get("estimated_cost_usd", 0.0)

    result = {
        "selected_model": state.get("selected_model"),
        "response_content": response_dict.get("content") if response_dict else None,
        "evaluation": evaluation,
        "routing_summary": {
            "all_candidates": routing_dict.get("all_candidates", []) if routing_dict else [],
            "eligible": routing_dict.get("eligible", []) if routing_dict else [],
            "pareto_frontier": routing_dict.get("pareto_frontier", []) if routing_dict else [],
        },
        "cost_usd": cost_usd,
        "retry_count": state.get("retry_count", 0),
        "stages_completed": state.get("stages_completed", []),
    }

    stages = list(state.get("stages_completed", []))
    stages.append("finalize")

    return {"result": result, "stages_completed": stages}
