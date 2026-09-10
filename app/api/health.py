# ---------------------------------------------------------------------------
# health.py — FastAPI health-check endpoints
# ---------------------------------------------------------------------------
# Exposes four probe endpoints used by load-balancers, orchestrators, and
# the Streamlit dashboard to determine whether the gateway is operational.
#
# Endpoints
# ---------
# GET /health          — combined liveness + readiness (convenience default)
# GET /health/live     — liveness:  process is alive and accepting requests
# GET /health/ready    — readiness: PostgreSQL, Redis, Langfuse, LangSmith
# GET /health/startup  — startup:   app finished initialising
# ---------------------------------------------------------------------------

import asyncio
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Response, status

from app.cache.connection import check_redis_health
from app.database.connection import check_postgres_health
from app.observability.connection import (
    check_langfuse_health,
    check_langsmith_health,
)

router = APIRouter(prefix="/health", tags=["health"])

# Internal flag — flipped to True once the app has completed its startup
# sequence (e.g. ran migrations, warmed caches).  The startup probe reads
# this so that orchestrators can wait until the app is truly ready.
_startup_complete: bool = False


def mark_startup_complete() -> None:
    """Called by ``app.main`` once initialisation finishes."""
    global _startup_complete
    _startup_complete = True


# -- /health/live -----------------------------------------------------------

@router.get("/live")
async def liveness() -> dict[str, Any]:
    """Liveness probe — always returns 200 if the process is up.

    Kubernetes / load-balancers use this to decide whether to restart or
    de-register the instance.  No dependency checks are performed here;
    those belong in the readiness probe.
    """
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# -- /health/ready ----------------------------------------------------------

@router.get("/ready")
async def readiness(response: Response) -> dict[str, Any]:
    """Readiness probe — verifies every critical backend is reachable.

    Each service check runs concurrently via ``asyncio.gather`` so that
    the overall latency is bounded by the slowest single check rather
    than their sum.
    """
    # Fire all four checks in parallel
    pg, redis, langfuse, langsmith = await asyncio.gather(
        check_postgres_health(),
        check_redis_health(),
        check_langfuse_health(),
        check_langsmith_health(),
    )

    services: dict[str, Any] = {
        "postgres": pg,
        "redis": redis,
        "langfuse": langfuse,
        "langsmith": langsmith,
    }

    # A service counts as "failing" when its status is literally "down".
    # "skipped" (unconfigured) is acceptable during local dev.
    failing = [
        name for name, info in services.items() if info["status"] == "down"
    ]

    # Pick an overall status: ok only when nothing is down.
    if not failing:
        overall = "ok"
    else:
        overall = "degraded"
        # Return 503 so orchestrators can detect the degraded state.
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": overall,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": services,
    }


# -- /health/startup --------------------------------------------------------

@router.get("/startup")
async def startup(response: Response) -> dict[str, Any]:
    """Startup probe — returns 200 only after the app has finished init.

    Use this in Kubernetes ``startupProbe`` so that readiness / liveness
    probes are not exercised before the app is ready.
    """
    if _startup_complete:
        return {
            "status": "ok",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "status": "starting",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# -- /health (convenience) --------------------------------------------------

@router.get("")
async def health() -> dict[str, Any]:
    """Convenience endpoint that returns liveness status.

    For full dependency information, call ``/health/ready`` explicitly.
    """
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": "LLM Cost Router is running",
    }
