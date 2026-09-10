# ---------------------------------------------------------------------------
# main.py — FastAPI application entry point
# ---------------------------------------------------------------------------
# Creates the ASGI application that Uvicorn serves.  This is the single
# place where routers, middleware, and startup / shutdown hooks are wired
# together.
#
# Run with:
#   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# ---------------------------------------------------------------------------

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import mark_startup_complete
from app.api.router import api_router


# -- Lifespan (startup / shutdown) ------------------------------------------

@asynccontextmanager
async def lifespan(application: FastAPI):
    """Async context manager that runs once at startup and once at shutdown.

    Startup tasks:
      - Mark the health startup probe as complete so /health/startup
        returns 200.
      - (Future) run Alembic migrations, warm caches, etc.

    Shutdown tasks:
      - (Future) close database pools, flush telemetry buffers, etc.
    """
    # --- startup ---
    mark_startup_complete()
    yield
    # --- shutdown ---


# -- Application factory ----------------------------------------------------

app = FastAPI(
    title="LLM Cost Router",
    description="Cost-aware multi-model AI gateway with intelligent routing",
    version="0.1.0",
    lifespan=lifespan,
)

# -- CORS (wide-open for local dev; tighten in production) -------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -- Mount the API router ---------------------------------------------------

app.include_router(api_router)


# -- Root-level health endpoint (no /api/v1 prefix) -------------------------
# Load-balancers and orchestrators typically hit ``/health`` directly, so we
# mount the same health router at the root as well.

from app.api.health import router as health_router  # noqa: E402

app.include_router(health_router)
