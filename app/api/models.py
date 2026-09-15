
# ---------------------------------------------------------------------------
# models.py — GET /api/v1/models
# ---------------------------------------------------------------------------
# Returns the seed model catalog so the dashboard and other consumers can
# inspect available models, their capabilities, and pricing.
# ---------------------------------------------------------------------------

from fastapi import APIRouter

from app.api.schemas import ApiResponse, ok
from app.models.catalog import build_default_registry

router = APIRouter(prefix="/models", tags=["models"])


@router.get("", response_model=ApiResponse)
async def list_models() -> ApiResponse:
    """Return every model in the default catalog."""
    registry = build_default_registry()
    models = [m.model_dump() for m in registry.get_all()]
    return ok(models)
