# ---------------------------------------------------------------------------
# connection.py — Redis health check
# ---------------------------------------------------------------------------
# Provides ``check_redis_health`` which opens a short-lived connection to the
# configured Redis instance and verifies it responds to PING.
# ---------------------------------------------------------------------------

import time
from typing import Any

import redis.asyncio as aioredis

from app.config.settings import get_settings


async def check_redis_health() -> dict[str, Any]:
    """Ping Redis and return a status dict.

    Returns
    -------
    dict
        ``{"status": "ok"|"down", "latency_ms": <float>, "error": <str|None>}``
    """
    settings = get_settings()
    client: aioredis.Redis | None = None

    try:
        # Create a short-lived async Redis client for the probe.
        client = aioredis.from_url(
            settings.redis_url,
            socket_connect_timeout=2,
        )

        start = time.perf_counter()
        pong = await client.ping()
        latency_ms = round((time.perf_counter() - start) * 1000, 2)

        if pong:
            return {"status": "ok", "latency_ms": latency_ms, "error": None}
        else:
            return {
                "status": "down",
                "latency_ms": latency_ms,
                "error": "PING did not return PONG",
            }

    except Exception as exc:
        return {
            "status": "down",
            "latency_ms": None,
            "error": str(exc),
        }

    finally:
        if client is not None:
            await client.aclose()
