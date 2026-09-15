# ---------------------------------------------------------------------------
# conftest.py — Shared pytest fixtures for the test suite
# ---------------------------------------------------------------------------

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest_asyncio.fixture
async def client():
    """Yield an ``httpx.AsyncClient`` wired directly to the FastAPI ASGI
    app — no real server is started, so tests stay fast and isolated.
    ``raise_app_exceptions=False`` mirrors a real server: unhandled errors
    are converted to 500 responses instead of propagating into tests."""
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac