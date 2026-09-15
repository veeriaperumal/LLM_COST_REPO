# ---------------------------------------------------------------------------
# test_middleware.py — Tests for request-context and logging middleware
# ---------------------------------------------------------------------------
# Uses POST /api/v1/route (offline, no external services) so header checks
# are deterministic.
# ---------------------------------------------------------------------------

import logging

import pytest


def _valid_body(**kw):
    body = {"task": "classification", "prompt": "some input text"}
    body.update(kw)
    return body


@pytest.mark.asyncio
async def test_request_id_and_correlation_headers_present(client):
    """Both identifier headers must be echoed on every response."""
    resp = await client.post("/api/v1/route", json=_valid_body())
    assert resp.status_code == 200
    assert "x-request-id" in resp.headers
    assert len(resp.headers["x-request-id"]) == 32  # uuid4 hex
    assert "x-correlation-id" in resp.headers


@pytest.mark.asyncio
async def test_inbound_correlation_id_is_honoured(client):
    """A client-supplied X-Correlation-ID should be echoed back."""
    resp = await client.post(
        "/api/v1/route",
        json=_valid_body(),
        headers={"X-Correlation-ID": "corr-abc-123"},
    )
    assert resp.status_code == 200
    assert resp.headers["x-correlation-id"] == "corr-abc-123"


@pytest.mark.asyncio
async def test_request_id_changes_between_requests(client):
    """Each request gets a fresh request ID."""
    r1 = await client.post("/api/v1/route", json=_valid_body())
    r2 = await client.post("/api/v1/route", json=_valid_body())
    assert r1.headers["x-request-id"] != r2.headers["x-request-id"]


@pytest.mark.asyncio
async def test_envelope_meta_matches_response_header(client):
    """The envelope's meta.request_id must equal the response header."""
    resp = await client.post("/api/v1/route", json=_valid_body())
    body = resp.json()
    assert body["meta"]["request_id"] == resp.headers["x-request-id"]
    assert body["meta"]["request_id"] != ""


@pytest.mark.asyncio
async def test_logging_middleware_emits_line(client, caplog):
    """One INFO log line must be emitted per request with status/duration."""
    with caplog.at_level(logging.INFO, logger="app.api.middleware"):
        await client.post("/api/v1/route", json=_valid_body())

    messages = [r.getMessage() for r in caplog.records]
    assert any("path=/api/v1/route" in m and "status=200" in m for m in messages)
    assert any("duration_ms=" in m for m in messages)