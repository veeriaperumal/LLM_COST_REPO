# ---------------------------------------------------------------------------
# main.py — FastAPI application entry point
# ---------------------------------------------------------------------------
# Creates the ASGI application that Uvicorn serves.  This is the single
# place where middleware, routers, and exception handlers are wired
# together.
#
# Run with:
#   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# ---------------------------------------------------------------------------

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.exceptions import register_exception_handlers
from app.api.health import router as health_router
from app.api.middleware import (
    RequestContextMiddleware,
    RequestLoggingMiddleware,
    configure_cors,
)
from app.api.router import api_router


# -- Lifespan (startup / shutdown) ------------------------------------------

@asynccontextmanager
async def lifespan(application: FastAPI):
    """Async context manager that runs once at startup and once at shutdown.

    Startup/shutdown hooks reserved for future work (Alembic migrations,
    pool warm-up, telemetry flush).  Nothing required yet.
    """
    yield


# -- Application factory ----------------------------------------------------

app = FastAPI(
    title="LLM Cost Router",
    description="Cost-aware multi-model AI gateway with intelligent routing",
    version="0.1.0",
    lifespan=lifespan,
)

# -- Middleware --------------------------------------------------------------
# Starlette wires middleware so the LAST one added runs FIRST.  We therefore
# add in this order to get: CORS -> request-context -> request-logging -> route.
#   - logging is added first  (runs last / innermost)  so the request ID is
#     already bound when its log line is emitted.
#   - context is added second (runs before logging)   so it can mint the ID.
#   - CORS is added last      (runs first / outermost) so preflight requests
#     are answered before any other logic.
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RequestContextMiddleware)
configure_cors(app)

# -- Exception handlers ------------------------------------------------------
# Every controlled and uncontrolled failure path returns the standard
# response envelope (see app/api/exceptions.py).
register_exception_handlers(app)

# -- Routers -----------------------------------------------------------------

# Business API under /api/v1 (health + route currently).
app.include_router(api_router)

# Root-level health probe (no prefix) so k8s / load-balancers can hit
# ``/health`` directly like any standard health check.
app.include_router(health_router)