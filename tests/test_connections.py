# ---------------------------------------------------------------------------
# test_connections.py — Unit tests for individual health-check functions
# ---------------------------------------------------------------------------
# These tests mock the external network calls so they never touch real
# PostgreSQL / Redis / Langfuse / LangSmith instances.
# ---------------------------------------------------------------------------

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.database.connection import check_postgres_health
from app.cache.connection import check_redis_health
from app.observability.connection import (
    check_langfuse_health,
    check_langsmith_health,
)


# -- PostgreSQL -------------------------------------------------------------

@pytest.mark.asyncio
async def test_postgres_ok():
    """Successful query should return status ok with a latency."""
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock()

    mock_engine = AsyncMock()
    mock_engine.connect = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_conn), __aexit__=AsyncMock()))
    mock_engine.dispose = AsyncMock()

    with patch("app.database.connection.create_async_engine", return_value=mock_engine):
        result = await check_postgres_health()

    assert result["status"] == "ok"
    assert result["latency_ms"] is not None
    assert result["error"] is None


@pytest.mark.asyncio
async def test_postgres_down_on_exception():
    """A connection error should return status down with the error string."""
    with patch(
        "app.database.connection.create_async_engine",
        side_effect=Exception("connection refused"),
    ):
        result = await check_postgres_health()

    assert result["status"] == "down"
    assert result["latency_ms"] is None
    assert "connection refused" in result["error"]


# -- Redis ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_redis_ok():
    """Successful PING should return status ok."""
    mock_client = AsyncMock()
    mock_client.ping = AsyncMock(return_value=True)
    mock_client.aclose = AsyncMock()

    with patch("app.cache.connection.aioredis.from_url", return_value=mock_client):
        result = await check_redis_health()

    assert result["status"] == "ok"
    assert result["latency_ms"] is not None
    assert result["error"] is None


@pytest.mark.asyncio
async def test_redis_down_on_exception():
    """A connection error should return status down."""
    with patch(
        "app.cache.connection.aioredis.from_url",
        side_effect=Exception("Connection refused"),
    ):
        result = await check_redis_health()

    assert result["status"] == "down"
    assert result["latency_ms"] is None
    assert "Connection refused" in result["error"]


# -- Langfuse ---------------------------------------------------------------

@pytest.mark.asyncio
async def test_langfuse_skipped_when_no_key():
    """If the public key is empty the check should report skipped."""
    with patch("app.observability.connection.get_settings") as mock:
        mock.return_value = MagicMock(langfuse_public_key="")
        result = await check_langfuse_health()

    assert result["status"] == "skipped"
    assert result["error"] == "LANGFUSE_PUBLIC_KEY not configured"


@pytest.mark.asyncio
async def test_langfuse_ok():
    """HTTP 200 from Langfuse should return status ok."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock()

    with (
        patch("app.observability.connection.get_settings") as mock_settings,
        patch("app.observability.connection.httpx.AsyncClient", return_value=mock_client),
    ):
        mock_settings.return_value = MagicMock(
            langfuse_public_key="pk-test",
            langfuse_host="https://cloud.langfuse.com",
        )
        result = await check_langfuse_health()

    assert result["status"] == "ok"
    assert result["error"] is None


@pytest.mark.asyncio
async def test_langfuse_down_on_500():
    """HTTP 500 from Langfuse should return status down."""
    mock_resp = MagicMock()
    mock_resp.status_code = 500

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock()

    with (
        patch("app.observability.connection.get_settings") as mock_settings,
        patch("app.observability.connection.httpx.AsyncClient", return_value=mock_client),
    ):
        mock_settings.return_value = MagicMock(
            langfuse_public_key="pk-test",
            langfuse_host="https://cloud.langfuse.com",
        )
        result = await check_langfuse_health()

    assert result["status"] == "down"
    assert "500" in result["error"]


@pytest.mark.asyncio
async def test_langfuse_down_on_network_error():
    """A network exception should return status down."""
    with (
        patch("app.observability.connection.get_settings") as mock_settings,
        patch(
            "app.observability.connection.httpx.AsyncClient",
            side_effect=Exception("DNS resolution failed"),
        ),
    ):
        mock_settings.return_value = MagicMock(
            langfuse_public_key="pk-test",
            langfuse_host="https://cloud.langfuse.com",
        )
        result = await check_langfuse_health()

    assert result["status"] == "down"
    assert "DNS resolution failed" in result["error"]


# -- LangSmith --------------------------------------------------------------

@pytest.mark.asyncio
async def test_langsmith_skipped_when_no_key():
    """If the API key is empty the check should report skipped."""
    with patch("app.observability.connection.get_settings") as mock:
        mock.return_value = MagicMock(langchain_api_key="")
        result = await check_langsmith_health()

    assert result["status"] == "skipped"
    assert result["error"] == "LANGCHAIN_API_KEY not configured"


@pytest.mark.asyncio
async def test_langsmith_ok():
    """HTTP 200 from LangSmith should return status ok."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock()

    with (
        patch("app.observability.connection.get_settings") as mock_settings,
        patch("app.observability.connection.httpx.AsyncClient", return_value=mock_client),
    ):
        mock_settings.return_value = MagicMock(langchain_api_key="ls-key")
        result = await check_langsmith_health()

    assert result["status"] == "ok"
    assert result["error"] is None


@pytest.mark.asyncio
async def test_langsmith_down_on_500():
    """HTTP 500 from LangSmith should return status down."""
    mock_resp = MagicMock()
    mock_resp.status_code = 500

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock()

    with (
        patch("app.observability.connection.get_settings") as mock_settings,
        patch("app.observability.connection.httpx.AsyncClient", return_value=mock_client),
    ):
        mock_settings.return_value = MagicMock(langchain_api_key="ls-key")
        result = await check_langsmith_health()

    assert result["status"] == "down"
    assert "500" in result["error"]


@pytest.mark.asyncio
async def test_langsmith_down_on_network_error():
    """A network exception should return status down."""
    with (
        patch("app.observability.connection.get_settings") as mock_settings,
        patch(
            "app.observability.connection.httpx.AsyncClient",
            side_effect=Exception("Connection timeout"),
        ),
    ):
        mock_settings.return_value = MagicMock(langchain_api_key="ls-key")
        result = await check_langsmith_health()

    assert result["status"] == "down"
    assert "Connection timeout" in result["error"]
