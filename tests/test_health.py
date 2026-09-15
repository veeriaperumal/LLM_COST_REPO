# ---------------------------------------------------------------------------
# test_health.py — Tests for the single consolidated /health endpoint
# ---------------------------------------------------------------------------

import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_health_ok_when_all_services_up(client):
    """When every backend is reachable, /health returns 200 with status ok."""
    mock_ok = AsyncMock(
        return_value={"status": "ok", "latency_ms": 1.0, "error": None}
    )
    with (
        patch("app.api.health.check_postgres_health", mock_ok),
        patch("app.api.health.check_redis_health", mock_ok),
        patch("app.api.health.check_langfuse_health", mock_ok),
        patch("app.api.health.check_langsmith_health", mock_ok),
    ):
        resp = await client.get("/health")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "timestamp" in body
    for svc in ("postgres", "redis", "langfuse", "langsmith"):
        assert body["services"][svc]["status"] == "ok"


@pytest.mark.asyncio
async def test_health_degraded_when_service_down(client):
    """With one service down the endpoint returns 503 and status degraded."""
    mock_ok = AsyncMock(
        return_value={"status": "ok", "latency_ms": 1.0, "error": None}
    )
    mock_down = AsyncMock(
        return_value={"status": "down", "latency_ms": None, "error": "mocked"}
    )
    with (
        patch("app.api.health.check_postgres_health", mock_ok),
        patch("app.api.health.check_redis_health", mock_down),
        patch("app.api.health.check_langfuse_health", mock_ok),
        patch("app.api.health.check_langsmith_health", mock_ok),
    ):
        resp = await client.get("/health")

    assert resp.status_code == 503
    body = resp.json()
    assert body["status"] == "degraded"
    assert body["services"]["redis"]["status"] == "down"


@pytest.mark.asyncio
async def test_health_skipped_services_not_counted_as_down(client):
    """Unconfigured (skipped) services must not degrade overall status."""
    mock_ok = AsyncMock(
        return_value={"status": "ok", "latency_ms": 1.0, "error": None}
    )
    mock_skipped = AsyncMock(
        return_value={
            "status": "skipped", "latency_ms": None, "error": "not configured",
        }
    )
    with (
        patch("app.api.health.check_postgres_health", mock_ok),
        patch("app.api.health.check_redis_health", mock_ok),
        patch("app.api.health.check_langfuse_health", mock_skipped),
        patch("app.api.health.check_langsmith_health", mock_skipped),
    ):
        resp = await client.get("/health")

    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    assert resp.json()["services"]["langfuse"]["status"] == "skipped"