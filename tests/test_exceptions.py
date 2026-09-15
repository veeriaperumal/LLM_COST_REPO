# ---------------------------------------------------------------------------
# test_exceptions.py — Tests for centralized error handling
# ---------------------------------------------------------------------------

import pytest
from unittest.mock import patch

from app.api.exceptions import (
    BudgetExceededError,
    InvalidInputError,
    NotFoundError,
    ServiceUnavailableError,
    UnauthorizedError,
    UpstreamError,
)


def test_app_error_subclasses_status_codes():
    """Each AppError subclass carries the intended HTTP status."""
    assert NotFoundError.status_code == 404
    assert InvalidInputError.status_code == 400
    assert UnauthorizedError.status_code == 401
    assert BudgetExceededError.status_code == 429
    assert UpstreamError.status_code == 502
    assert ServiceUnavailableError.status_code == 503


def test_app_error_custom_overrides():
    """Instances may override status code and code at construction."""
    err = NotFoundError("gone", status_code=410, code="MODEL_REMOVED")
    assert err.status_code == 410
    assert err.code == "MODEL_REMOVED"
    assert err.message == "gone"
    assert err.details is None


@pytest.mark.asyncio
async def test_validation_error_returns_422_envelope(client):
    """A malformed request body yields a 422 envelope, not FastAPI's raw
    default error."""
    resp = await client.post("/api/v1/route", json={})  # missing required field
    assert resp.status_code == 422
    body = resp.json()
    assert body["success"] is False
    assert body["data"] is None
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert isinstance(body["error"]["details"], list)
    assert body["meta"]["request_id"]


@pytest.mark.asyncio
async def test_http_exception_returns_404_envelope(client):
    """Unknown paths produce the standard envelope."""
    resp = await client.get("/api/v1/does-not-exist")
    assert resp.status_code == 404
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "HTTP_ERROR"


@pytest.mark.asyncio
async def test_routing_error_maps_to_400_envelope(client):
    """RoutingFailure surfaces as INVALID_INPUT."""
    # A budget so tight that every model is rejected -> RoutingError.
    resp = await client.post(
        "/api/v1/route",
        json={"task": "classification", "prompt": "x", "max_cost_usd": 1e-9},
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "INVALID_INPUT"
    assert "No models" in body["error"]["message"] or "rejected" in body["error"]["message"]


@pytest.mark.asyncio
async def test_unhandled_exception_returns_500_masked(client):
    """Unexpected failures return 500 with a generic message, never leaking
    the exception text."""
    with patch(
        "app.api.route.default_engine",
        side_effect=RuntimeError("internal-db-password-leak"),
    ):
        resp = await client.post(
            "/api/v1/route",
            json={"task": "classification", "prompt": "hello"},
        )

    assert resp.status_code == 500
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "INTERNAL_ERROR"
    assert body["error"]["message"] == "Internal server error"
    assert "password" not in body["error"]["message"]