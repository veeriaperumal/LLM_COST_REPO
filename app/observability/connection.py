# ---------------------------------------------------------------------------
# connection.py — Langfuse & LangSmith connectivity checks
# ---------------------------------------------------------------------------
# Two lightweight async probes that verify the observability backends are
# reachable.  They use httpx rather than the full SDKs so that a failure
# in one service does not block the other.
# ---------------------------------------------------------------------------

import time
from typing import Any

import httpx

from app.config.settings import get_settings


async def check_langfuse_health() -> dict[str, Any]:
    """Probe the Langfuse health / hello endpoint.

    Langfuse exposes a ``/api/public/health`` path that returns 200 when the
    instance is operational.  If the public key is empty we skip the network
    call and report ``"skipped"`` so that local dev without Langfuse still
    passes readiness.

    Returns
    -------
    dict
        ``{"status": "ok"|"down"|"skipped", "latency_ms": <float|None>, "error": <str|None>}``
    """
    settings = get_settings()

    # If no key is configured the service is not expected to be reachable.
    if not settings.langfuse_public_key:
        return {
            "status": "skipped",
            "latency_ms": None,
            "error": "LANGFUSE_PUBLIC_KEY not configured",
        }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            start = time.perf_counter()
            resp = await client.get(
                f"{settings.langfuse_host}/api/public/health",
                headers={
                    "Authorization": f"Bearer {settings.langfuse_public_key}",
                },
            )
            latency_ms = round((time.perf_counter() - start) * 1000, 2)

            if resp.status_code == 200:
                return {
                    "status": "ok",
                    "latency_ms": latency_ms,
                    "error": None,
                }
            else:
                return {
                    "status": "down",
                    "latency_ms": latency_ms,
                    "error": f"HTTP {resp.status_code}",
                }

    except Exception as exc:
        return {
            "status": "down",
            "latency_ms": None,
            "error": str(exc),
        }


async def check_langsmith_health() -> dict[str, Any]:
    """Probe the LangSmith / LangChain Tracing API.

    LangSmith does not expose a dedicated health endpoint, so we call the
    ``/api/v1/sessions`` list endpoint (which requires a valid API key) and
    treat a non-5xx response as proof that the backend is reachable.

    Returns
    -------
    dict
        ``{"status": "ok"|"down"|"skipped", "latency_ms": <float|None>, "error": <str|None>}``
    """
    settings = get_settings()

    if not settings.langchain_api_key:
        return {
            "status": "skipped",
            "latency_ms": None,
            "error": "LANGCHAIN_API_KEY not configured",
        }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            start = time.perf_counter()
            resp = await client.get(
                "https://api.smith.langchain.com/api/v1/sessions",
                headers={
                    "x-api-key": settings.langchain_api_key,
                },
            )
            latency_ms = round((time.perf_counter() - start) * 1000, 2)

            # We only care that the service is up — 200-499 all count.
            if resp.status_code < 500:
                return {
                    "status": "ok",
                    "latency_ms": latency_ms,
                    "error": None,
                }
            else:
                return {
                    "status": "down",
                    "latency_ms": latency_ms,
                    "error": f"HTTP {resp.status_code}",
                }

    except Exception as exc:
        return {
            "status": "down",
            "latency_ms": None,
            "error": str(exc),
        }
