# ---------------------------------------------------------------------------
# test_settings.py — Tests for the Pydantic BaseSettings config
# ---------------------------------------------------------------------------

import pytest

from app.config.settings import Settings, get_settings


def test_settings_defaults():
    """Settings should fall back to defaults when env vars are absent."""
    s = Settings()
    assert s.app_name == "llm-cost-router"
    assert s.debug is False
    # Defaults point at localhost
    assert "localhost" in s.database_url
    assert "localhost" in s.redis_url


def test_settings_singleton():
    """get_settings() should return the same instance on repeated calls."""
    a = get_settings()
    b = get_settings()
    assert a is b


def test_settings_langfuse_defaults():
    """Langfuse keys default to empty string when not configured."""
    s = Settings()
    assert s.langfuse_public_key == ""
    assert s.langfuse_secret_key == ""
    assert s.langfuse_host == "https://cloud.langfuse.com"


def test_settings_langsmith_defaults():
    """LangSmith keys default to empty string when not configured."""
    s = Settings()
    assert s.langchain_api_key == ""
    assert s.langchain_tracing_v2 is True
    assert s.langchain_project == "llm-cost-router"
