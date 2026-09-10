# ---------------------------------------------------------------------------
# router.py — Top-level API router aggregation
# ---------------------------------------------------------------------------
# Collects every sub-router from the ``app.api`` package and re-exports a
# single ``api_router`` that the FastAPI application mounts in one step.
# ---------------------------------------------------------------------------

from fastapi import APIRouter

from app.api.health import router as health_router

# Master router — all API sub-routers are included here.
api_router = APIRouter(prefix="/api/v1")

api_router.include_router(health_router)
