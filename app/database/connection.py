# ---------------------------------------------------------------------------
# connection.py — PostgreSQL async health check
# ---------------------------------------------------------------------------
# Provides ``check_postgres_health`` which opens a short-lived connection to
# the configured PostgreSQL database and verifies it is reachable.
# ---------------------------------------------------------------------------

import time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy import text

from app.config.settings import get_settings


async def check_postgres_health() -> dict[str, Any]:
    """Ping PostgreSQL and return a status dict.

    Returns
    -------
    dict
        ``{"status": "ok"|"down", "latency_ms": <float>, "error": <str|None>}``
    """
    settings = get_settings()
    engine: AsyncEngine | None = None

    try:
        # Create a throw-away engine; the connection pool is tiny and fast
        # enough for a health probe.  In production a shared engine would be
        # preferable, but for Phase 0 this keeps the check self-contained.
        engine = create_async_engine(
            settings.database_url,
            pool_pre_ping=True,
            pool_size=1,
        )

        start = time.perf_counter()
        async with engine.connect() as conn:
            # ``SELECT 1`` is the cheapest server-side round-trip
            await conn.execute(text("SELECT 1"))
        latency_ms = round((time.perf_counter() - start) * 1000, 2)

        return {"status": "ok", "latency_ms": latency_ms, "error": None}

    except Exception as exc:
        # Any exception means the database is unreachable or misconfigured.
        return {
            "status": "down",
            "latency_ms": None,
            "error": str(exc),
        }

    finally:
        # Dispose the engine so we don't leak connections.
        if engine is not None:
            await engine.dispose()
