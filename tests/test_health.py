# ---------------------------------------------------------------------------
# test_health.py — Tests for all /health endpoints
# ---------------------------------------------------------------------------

import pytest
import pytest_asyncio


# -- GET /health -----------------------------------------------------------

@pytest.mark.asyncio
async def test_health_root_returns_ok(client):
    """The root /health endpoint should return 200 with status ok."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "timestamp" in body
    assert "LLM Cost Router" in body["message"]


# -- GET /health/live ------------------------------------------------------

@pytest.mark.asyncio
async def test_liveness_returns_ok(client):
    """/health/live must always return 200."""
    resp = await client.get("/health/live")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "timestamp" in body


# -- GET /health/startup ---------------------------------------------------

@pytest.mark.asyncio
async def test_startup_returns_ok_after_init(client):
    """/health/startup should return 200 once lifespan has completed.

    The conftest client fixture calls mark_startup_complete() so the flag
    is already True when this test runs.
    """
    resp = await client.get("/health/startup")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"


@pytest.mark.asyncio
async def test_startup_status_field(client):
    """Startup body must contain a status string."""
    resp = await client.get("/health/startup")
    body = resp.json()
    assert isinstance(body["status"], str)


# -- GET /health/ready (all external services mocked as "down") -----------

@pytest.mark.asyncio
async def test_readiness_degraded_when_all_services_down(client):
    """When every backend is unreachable the endpoint must return 503
    with overall status ``degraded`` and individual ``down`` entries."""
    # Patch every checker to return "down"
    from unittest.mock import AsyncMock, patch

    mock_down = AsyncMock(
        return_value={"status": "down", "latency_ms": None, "error": "mocked"}
    )

    with (
        patch("app.api.health.check_postgres_health", mock_down),
        patch("app.api.health.check_redis_health", mock_down),
        patch("app.api.health.check_langfuse_health", mock_down),
        patch("app.api.health.check_langsmith_health", mock_down),
    ):
        resp = await client.get("/health/ready")
        assert resp.status_code == 503
        body = resp.json()
        assert body["status"] == "degraded"
        for svc in ("postgres", "redis", "langfuse", "langsmith"):
            assert body["services"][svc]["status"] == "down"


@pytest.mark.asyncio
async def test_readiness_ok_when_all_services_ok(client):
    """When every backend is reachable the endpoint must return 200
    with overall status ``ok``."""
    from unittest.mock import AsyncMock, patch

    mock_ok = AsyncMock(
        return_value={"status": "ok", "latency_ms": 1.23, "error": None}
    )

    with (
        patch("app.api.health.check_postgres_health", mock_ok),
        patch("app.api.health.check_redis_health", mock_ok),
        patch("app.api.health.check_langfuse_health", mock_ok),
        patch("app.api.health.check_langsmith_health", mock_ok),
    ):
        resp = await client.get("/health/ready")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        for svc in ("postgres", "redis", "langfuse", "langsmith"):
            assert body["services"][svc]["status"] == "ok"


@pytest.mark.asyncio
async def test_readiness_degraded_when_one_service_down(client):
    """If a single service is down while others are ok, overall status is
    ``degraded`` and the response is 503."""
    from unittest.mock import AsyncMock, patch

    mock_ok = AsyncMock(
        return_value={"status": "ok", "latency_ms": 1.0, "error": None}
    )
    mock_down = AsyncMock(
        return_value={"status": "down", "latency_ms": None, "error": "nope"}
    )

    with (
        patch("app.api.health.check_postgres_health", mock_ok),
        patch("app.api.health.check_redis_health", mock_down),
        patch("app.api.health.check_langfuse_health", mock_ok),
        patch("app.api.health.check_langsmith_health", mock_ok),
    ):
        resp = await client.get("/health/ready")
        assert resp.status_code == 503
        body = resp.json()
        assert body["status"] == "degraded"
        assert body["services"]["redis"]["status"] == "down"
        assert body["services"]["postgres"]["status"] == "ok"


@pytest.mark.asyncio
async def test_readiness_skipped_services_not_counted_as_down(client):
    """A service returning ``"skipped"`` (unconfigured) must NOT be treated
    as ``"down"``."""
    from unittest.mock import AsyncMock, patch

    mock_ok = AsyncMock(
        return_value={"status": "ok", "latency_ms": 1.0, "error": None}
    )
    mock_skipped = AsyncMock(
        return_value={
            "status": "skipped",
            "latency_ms": None,
            "error": "not configured",
        }
    )

    with (
        patch("app.api.health.check_postgres_health", mock_ok),
        patch("app.api.health.check_redis_health", mock_ok),
        patch("app.api.health.check_langfuse_health", mock_skipped),
        patch("app.api.health.check_langsmith_health", mock_skipped),
    ):
        resp = await client.get("/health/ready")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["services"]["langfuse"]["status"] == "skipped"


@pytest.mark.asyncio
async def test_readiness_body_has_timestamp(client):
    """Readiness response must include an ISO timestamp."""
    from unittest.mock import AsyncMock, patch

    mock_ok = AsyncMock(
        return_value={"status": "ok", "latency_ms": 1.0, "error": None}
    )
    with (
        patch("app.api.health.check_postgres_health", mock_ok),
        patch("app.api.health.check_redis_health", mock_ok),
        patch("app.api.health.check_langfuse_health", mock_ok),
        patch("app.api.health.check_langsmith_health", mock_ok),
    ):
        resp = await client.get("/health/ready")
        body = resp.json()
        assert "timestamp" in body


# -- Startup probe internal state -------------------------------------------

@pytest.mark.asyncio
async def test_mark_startup_complete_changes_state(client):
    """After the conftest client fixture runs, mark_startup_complete()
    should have been called and the flag should be True."""
    from app.api.health import _startup_complete

    assert _startup_complete is True
