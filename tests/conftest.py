# ---------------------------------------------------------------------------
# conftest.py — Shared pytest fixtures for the test suite
# ---------------------------------------------------------------------------

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.health import mark_startup_complete


@pytest_asyncio.fixture
async def client():
    """Yield an ``httpx.AsyncClient`` wired directly to the FastAPI ASGI
    app — no real server is started, so tests stay fast and isolated.

    Because ``httpx.ASGITransport`` does not invoke the ASGI lifespan, we
    manually call ``mark_startup_complete()`` here so that the startup
    probe behaves as it would in production.
    """
    mark_startup_complete()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
