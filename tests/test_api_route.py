# ---------------------------------------------------------------------------
# test_api_route.py — End-to-end tests for POST /api/v1/route
# ---------------------------------------------------------------------------

import pytest


def _body(**kw):
    body = {"task": "classification", "prompt": "classify this"}
    body.update(kw)
    return body


@pytest.mark.asyncio
async def test_route_success_envelope(client):
    """A valid routing request returns 200 with a populated envelope."""
    resp = await client.post("/api/v1/route", json=_body())
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["error"] is None
    assert isinstance(body["data"]["selected_model"], str)
    assert body["data"]["decision_log"]  # non-empty
    assert body["meta"]["request_id"]


@pytest.mark.asyncio
async def test_route_honours_constraints(client):
    """Toold-calling constraint still routes (gpt-4o / claude-sonnet)."""
    resp = await client.post(
        "/api/v1/route", json=_body(require_tools=True)
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True


@pytest.mark.asyncio
async def test_route_with_budget_failure(client):
    """An impossible budget must fail with the error envelope."""
    resp = await client.post(
        "/api/v1/route",
        json=_body(max_cost_usd=1e-9),
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["success"] is False
    assert body["data"] is None
    assert body["error"]["code"] == "INVALID_INPUT"