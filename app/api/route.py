# ---------------------------------------------------------------------------
# route.py — POST /api/v1/route and POST /api/v1/route/graph
# ---------------------------------------------------------------------------
# The /route endpoint demonstrates the standard envelope using the Phase 3
# RouterEngine directly.  The /route/graph endpoint invokes the full
# LangGraph state machine for stateful orchestration with checkpointing.
# ---------------------------------------------------------------------------

import uuid

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.api.exceptions import InvalidInputError
from app.api.schemas import ApiResponse, ok
from app.models.schemas import TaskType
from app.router.engine import RoutingError, default_engine
from app.router.schemas import RoutingRequest

router = APIRouter(prefix="/route", tags=["route"])


class RouteRequest(BaseModel):
    """Request body for /api/v1/route — mirrors RoutingRequest fields."""

    task: TaskType
    prompt: str = ""
    estimated_input_tokens: int | None = Field(
        default=None, ge=0, description="Estimated prompt tokens; None -> heuristic"
    )
    estimated_output_tokens: int = Field(default=256, ge=0)
    require_structured_output: bool = False
    require_tools: bool = False
    min_context_tokens: int = 0
    max_cost_usd: float | None = Field(default=None, ge=0)
    unavailable_models: set[str] = Field(default_factory=set)


@router.post("", response_model=ApiResponse)
async def route_request(payload: RouteRequest) -> ApiResponse:
    """Route a single request through the cost-aware engine."""
    engine = default_engine()

    try:
        result = engine.route(RoutingRequest(**payload.model_dump()))
    except RoutingError as exc:
        raise InvalidInputError(exc.message) from exc

    return ok(result.model_dump())


@router.post("/graph", response_model=ApiResponse)
async def route_request_graph(payload: RouteRequest) -> ApiResponse:
    """Route a request through the full LangGraph state machine.

    The workflow runs: analyze → filter → route → execute → evaluate → finalize.
    Persistent checkpoints allow resumption after interruptions.
    """
    from app.graph.builder import build_graph

    graph = build_graph()

    initial_state = {
        "request": RoutingRequest(**payload.model_dump()).model_dump(),
        "routing_result": None,
        "selected_model": None,
        "provider_response": None,
        "evaluation": {"score": 0.0, "status": "pending", "reason": ""},
        "retry_count": 0,
        "max_retries": 2,
        "unavailable_models": list(payload.unavailable_models),
        "mcp_tool_results": [],
        "result": None,
        "error": None,
        "stages_completed": [],
    }

    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    try:
        final_state = await graph.ainvoke(initial_state, config=config)
    except Exception as exc:
        raise InvalidInputError(f"Graph execution failed: {exc}") from exc

    result = final_state.get("result")
    if result is None:
        error = final_state.get("error") or "Graph produced no result"
        raise InvalidInputError(error)

    return ok(result)