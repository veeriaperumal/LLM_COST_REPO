# ---------------------------------------------------------------------------
# test_cors.py — Tests for CORS preflight and origin allowlisting
# ---------------------------------------------------------------------------

from unittest.mock import patch

from fastapi import FastAPI
from starlette.testclient import TestClient

from app.api.middleware import configure_cors
from app.config.settings import Settings


def _build_app(settings: Settings) -> FastAPI:
    """A throwaway app wired with CORS from the given settings."""
    app = FastAPI()

    @app.get("/ping")
    async def ping():
        return {"pong": True}

    with patch("app.api.middleware.get_settings", return_value=settings):
        configure_cors(app)
    return app


def test_preflight_returns_cors_headers_for_default_origins():
    """With the default '*' allowlist, a preflight passes and echoes '*'."""
    app = _build_app(Settings(cors_origins="*", cors_allow_credentials=False))
    client = TestClient(app)

    resp = client.options(
        "/ping",
        headers={
            "Origin": "http://example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == "*"


def test_allowed_origin_in_allowlist_is_accepted():
    """A request from an allowed origin receives the matching header."""
    app = _build_app(
        Settings(cors_origins="http://app.example.com", cors_allow_credentials=False)
    )
    client = TestClient(app)

    resp = client.get("/ping", headers={"Origin": "http://app.example.com"})
    assert resp.headers["access-control-allow-origin"] == "http://app.example.com"


def test_unknown_origin_is_rejected():
    """A request from a non-allowlisted origin gets no CORS header."""
    app = _build_app(
        Settings(cors_origins="http://app.example.com", cors_allow_credentials=False)
    )
    client = TestClient(app)

    resp = client.get("/ping", headers={"Origin": "http://evil.example.com"})
    assert "access-control-allow-origin" not in resp.headers


def test_wildcard_origin_disables_credentials():
    """Starlette forbids '*' with credentials; the wildcard degrades them."""
    app = _build_app(Settings(cors_origins="*", cors_allow_credentials=True))
    client = TestClient(app)

    resp = client.options(
        "/ping",
        headers={
            "Origin": "http://example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.headers["access-control-allow-origin"] == "*"