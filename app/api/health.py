# ---------------------------------------------------------------------------
# health.py — Single consolidated health-check endpoint
# ---------------------------------------------------------------------------
# GET /health  — verifies liveness AND readiness in one probe: PostgreSQL,
# Redis, Langfuse, and LangSmith are checked concurrently.  Returns 200 when
# every service is reachable and 503 when any is down, using raw JSON payloads
# as expected by k8s / load-balancer probes.
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


@router.get("")
async def health(response: Response) -> dict[str, Any]:
    """Liveness + readiness in one call.

    Each service check runs concurrently via ``asyncio.gather`` so that
    the overall latency is bounded by the slowest single check rather
    than their sum.
    """
    # Fire all four checks in parallel.
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
    # "skipped" (not configured) is acceptable during local development.
    failing = [
        name for name, info in services.items() if info["status"] == "down"
    ]

    # Overall status: ok only when nothing is down.
    if failing:
        # Return 503 so orchestrators can detect the degraded state.
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        overall = "degraded"
    else:
        overall = "ok"

    return {
        "status": overall,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": services,
    }