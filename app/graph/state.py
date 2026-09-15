# ---------------------------------------------------------------------------
# state.py — TypedDict state schema for the LangGraph workflow
# ---------------------------------------------------------------------------
# Every node reads from and writes to this shared state.  The checkpointer
# serialises it automatically so the workflow can resume after restarts.
#
# Annotated keys allow multiple writes per step (required when nodes
# share keys and the graph may execute them in a single superstep).
# ---------------------------------------------------------------------------

from __future__ import annotations

from typing import Annotated, Any, TypedDict

from langgraph.graph.message import add_messages

from app.router.schemas import RoutingRequest, RoutingResult


def _override(existing: Any, new: Any) -> Any:
    """Reducer: last-write-wins for plain scalar keys."""
    return new


def _append_list(existing: list, new: list) -> list:
    """Reducer: extend lists across steps."""
    return existing + new


class GraphState(TypedDict, total=False):
    """Shared state carried through the LangGraph workflow."""

    # Input
    request: Annotated[dict, _override]

    # Routing
    routing_result: Annotated[dict | None, _override]
    selected_model: Annotated[str | None, _override]

    # Execution
    provider_response: Annotated[dict | None, _override]

    # Evaluation
    evaluation: Annotated[dict, _override]

    # Retry / escalation
    retry_count: Annotated[int, _override]
    max_retries: Annotated[int, _override]
    unavailable_models: Annotated[list[str], _append_list]

    # MCP tools
    mcp_tool_results: Annotated[list[dict], _append_list]

    # Final output
    result: Annotated[dict | None, _override]
    error: Annotated[str | None, _override]

    # Audit trail
    stages_completed: Annotated[list[str], _append_list]
