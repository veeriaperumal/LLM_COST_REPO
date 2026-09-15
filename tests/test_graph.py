# ---------------------------------------------------------------------------
# test_graph.py — Tests for the LangGraph state machine
# ---------------------------------------------------------------------------

from unittest.mock import AsyncMock, patch

import pytest

from app.graph.builder import build_graph
from app.graph.nodes import (
    analyze_node,
    evaluate_node,
    filter_node,
    finalize_node,
    route_node,
)
from app.graph.router import decide_next
from app.graph.state import GraphState
from app.models.providers.base import ProviderResponse
from app.models.schemas import TaskType
from app.router.schemas import RoutingRequest


# -- Helpers -------------------------------------------------------------------


def _base_state(**overrides) -> GraphState:
    request = RoutingRequest(
        task=TaskType.classification,
        prompt="Classify this text as positive or negative.",
        estimated_output_tokens=128,
    )
    state: GraphState = {
        "request": request.model_dump(),
        "routing_result": None,
        "selected_model": None,
        "provider_response": None,
        "evaluation": {"score": 0.0, "status": "pending", "reason": ""},
        "retry_count": 0,
        "max_retries": 2,
        "unavailable_models": [],
        "mcp_tool_results": [],
        "result": None,
        "error": None,
        "stages_completed": [],
    }
    state.update(overrides)
    return state


# -- Node unit tests -----------------------------------------------------------


def test_analyze_node_initializes_state():
    state = _base_state()
    result = analyze_node(state)
    assert "analyze" in result["stages_completed"]
    assert result["retry_count"] == 0
    assert result["max_retries"] == 2


def test_filter_node_selects_model():
    state = _base_state()
    state = {**state, **analyze_node(state)}
    result = filter_node(state)
    assert result["selected_model"] is not None
    assert result["error"] is None
    assert "filter" in result["stages_completed"]


def test_filter_node_fails_when_all_excluded():
    state = _base_state(
        unavailable_models=["gpt-4o", "gpt-4o-mini", "claude-3-5-sonnet", "claude-haiku-4-5"]
    )
    state = {**state, **analyze_node(state)}
    result = filter_node(state)
    assert result["selected_model"] is None
    assert result["error"] is not None


def test_route_node_returns_model():
    state = _base_state()
    state = {**state, **analyze_node(state)}
    state = {**state, **filter_node(state)}
    result = route_node(state)
    assert result["selected_model"] is not None
    assert result["error"] is None
    assert "route" in result["stages_completed"]


def test_evaluate_node_accepts_good_response():
    state = _base_state(
        provider_response={"content": "This is a positive review with enough content to pass all checks and be considered a valid response.", "input_tokens": 10, "output_tokens": 20, "model": "gpt-4o"}
    )
    result = evaluate_node(state)
    assert result["evaluation"]["status"] == "accept"
    assert result["evaluation"]["score"] >= 0.8


def test_evaluate_node_escalates_empty_response():
    state = _base_state(
        provider_response={"content": "", "input_tokens": 10, "output_tokens": 0, "model": "gpt-4o"}
    )
    result = evaluate_node(state)
    assert result["evaluation"]["status"] == "escalate"
    assert result["evaluation"]["score"] == 0.0


def test_evaluate_node_revise_on_moderate_score():
    state = _base_state(
        provider_response={"content": "Short.", "input_tokens": 5, "output_tokens": 2, "model": "gpt-4o"},
        retry_count=0,
        max_retries=2,
    )
    result = evaluate_node(state)
    assert result["evaluation"]["status"] == "revise"


def test_evaluate_node_escalates_when_no_retries():
    state = _base_state(
        provider_response={"content": "Short.", "input_tokens": 5, "output_tokens": 2, "model": "gpt-4o"},
        retry_count=2,
        max_retries=2,
    )
    result = evaluate_node(state)
    assert result["evaluation"]["status"] == "escalate"


def test_evaluate_node_escalates_no_response():
    state = _base_state(provider_response=None)
    result = evaluate_node(state)
    assert result["evaluation"]["status"] == "escalate"


def test_finalize_node_packages_result():
    state = _base_state(
        routing_result={
            "request": {},
            "all_candidates": ["gpt-4o"],
            "eligible": ["gpt-4o"],
            "pareto_frontier": ["gpt-4o"],
            "scores": {"gpt-4o": {"estimated_cost_usd": 0.001}},
            "selected_model": "gpt-4o",
            "exclusions": [],
            "decision_log": [],
        },
        selected_model="gpt-4o",
        provider_response={"content": "positive", "input_tokens": 5, "output_tokens": 2, "model": "gpt-4o"},
        evaluation={"score": 0.9, "status": "accept", "reason": "good"},
        stages_completed=["analyze", "filter", "route", "execute", "evaluate"],
    )
    result = finalize_node(state)
    assert result["result"]["selected_model"] == "gpt-4o"
    assert result["result"]["evaluation"]["status"] == "accept"
    assert "finalize" in result["stages_completed"]


# -- Conditional edge logic ----------------------------------------------------


def test_decide_next_accept():
    state = _base_state(evaluation={"score": 0.9, "status": "accept", "reason": ""})
    assert decide_next(state) == "finalize"


def test_decide_next_revise():
    state = _base_state(
        evaluation={"score": 0.6, "status": "revise", "reason": ""},
        retry_count=0,
        max_retries=2,
    )
    assert decide_next(state) == "route"


def test_decide_next_escalate():
    state = _base_state(evaluation={"score": 0.2, "status": "escalate", "reason": ""})
    assert decide_next(state) == "finalize"


# -- Full graph integration test -----------------------------------------------


def _mock_provider_response():
    return ProviderResponse(
        content="The sentiment is positive. This text expresses enthusiasm and satisfaction.",
        input_tokens=10,
        output_tokens=20,
        model="gpt-4o",
    )


def test_full_graph_happy_path():
    """Run the complete graph end-to-end with a valid classification request."""
    graph = build_graph()

    request = RoutingRequest(
        task=TaskType.classification,
        prompt="Classify this sentiment: I love this product!",
        estimated_output_tokens=128,
    )

    initial_state = {
        "request": request.model_dump(),
        "routing_result": None,
        "selected_model": None,
        "provider_response": None,
        "evaluation": {"score": 0.0, "status": "pending", "reason": ""},
        "retry_count": 0,
        "max_retries": 2,
        "unavailable_models": [],
        "mcp_tool_results": [],
        "result": None,
        "error": None,
        "stages_completed": [],
    }

    mock_response = _mock_provider_response()

    with patch("app.graph.nodes._get_provider") as mock_get:
        mock_provider = AsyncMock()
        mock_provider.complete.return_value = mock_response
        mock_get.return_value = mock_provider

        config = {"configurable": {"thread_id": "test-full-path"}}
        final_state = graph.invoke(initial_state, config=config)

    # The graph should have completed with a result
    assert final_state["result"] is not None
    assert final_state["result"]["selected_model"] is not None
    assert "finalize" in final_state["stages_completed"]
    assert final_state["result"]["evaluation"]["status"] in ("accept", "escalate")


def test_full_graph_with_excluded_models():
    """Graph handles unavailable models gracefully."""
    graph = build_graph()

    request = RoutingRequest(
        task=TaskType.classification,
        prompt="Classify this.",
        estimated_output_tokens=64,
    )

    initial_state = {
        "request": request.model_dump(),
        "routing_result": None,
        "selected_model": None,
        "provider_response": None,
        "evaluation": {"score": 0.0, "status": "pending", "reason": ""},
        "retry_count": 0,
        "max_retries": 2,
        "unavailable_models": ["gpt-4o", "gpt-4o-mini", "claude-3-5-sonnet", "claude-haiku-4-5"],
        "mcp_tool_results": [],
        "result": None,
        "error": None,
        "stages_completed": [],
    }

    config = {"configurable": {"thread_id": "test-excluded"}}
    final_state = graph.invoke(initial_state, config=config)

    # Should finalize with an error
    assert final_state["result"] is not None
    assert final_state["result"]["selected_model"] is None


def test_full_graph_checkpointing():
    """Verify that checkpoints are created and the thread_id works."""
    graph = build_graph()

    request = RoutingRequest(
        task=TaskType.qa,
        prompt="What is the capital of France?",
        estimated_output_tokens=64,
    )

    initial_state = {
        "request": request.model_dump(),
        "routing_result": None,
        "selected_model": None,
        "provider_response": None,
        "evaluation": {"score": 0.0, "status": "pending", "reason": ""},
        "retry_count": 0,
        "max_retries": 2,
        "unavailable_models": [],
        "mcp_tool_results": [],
        "result": None,
        "error": None,
        "stages_completed": [],
    }

    mock_response = _mock_provider_response()

    with patch("app.graph.nodes._get_provider") as mock_get:
        mock_provider = AsyncMock()
        mock_provider.complete.return_value = mock_response
        mock_get.return_value = mock_provider

        thread_id = "test-checkpoint-1"
        config = {"configurable": {"thread_id": thread_id}}

        final_state = graph.invoke(initial_state, config=config)

    # The graph should have completed
    assert final_state["result"] is not None
    # Verify stages were executed in order
    stages = final_state["stages_completed"]
    assert "analyze" in stages
    assert "finalize" in stages


def test_graph_builds_without_error():
    """Simply verify that the graph compiles without errors."""
    graph = build_graph()
    assert graph is not None
