# ---------------------------------------------------------------------------
# route.py — POST /api/v1/route
# ---------------------------------------------------------------------------
# Demonstrates the standard envelope, error handling, and CORS in one place:
# accepts a routing request, delegates to the Phase 3 RouterEngine, and wraps
# the result in the ApiResponse envelope.  Routing failures surface as a
# 400 INVALID_INPUT error.
# ---------------------------------------------------------------------------

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
        # Translate a failed routing decision into a standard error.
        raise InvalidInputError(exc.message) from exc

    return ok(result.model_dump())