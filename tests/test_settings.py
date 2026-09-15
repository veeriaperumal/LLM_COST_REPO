# ---------------------------------------------------------------------------
# test_settings.py — Tests for the Pydantic BaseSettings config
# ---------------------------------------------------------------------------

import os
from unittest.mock import patch

import pytest

from app.config.settings import Settings, get_settings


def _fresh_settings(**overrides: str | None) -> Settings:
    """Create a Settings instance with env vars cleared so defaults apply.

    The project's .env file may set empty values (e.g. ``DATABASE_URL=``)
    which pydantic-settings treats as explicit overrides.  This helper
    strips those out so the class defaults are exercised.
    """
    # Build a clean env dict with all project keys removed
    clean_env = {
        k: v
        for k, v in os.environ.items()
        if k
        in {
            # Only keep vars that are NOT part of our Settings model
        }
        or not k.startswith(
            (
                "DATABASE_URL",
                "REDIS_URL",
                "LANGFUSE_",
                "LANGCHAIN_",
                "PROVIDER_API_KEY",
                "APP_NAME",
                "DEBUG",
                "OPENAI_API_KEY",
                "ANTHROPIC_API_KEY",
                "CORS_",
            )
        )
    }
    clean_env.update(overrides)
    with patch.dict(os.environ, clean_env, clear=True):
        return Settings(_env_file=None)


def test_settings_defaults():
    """Settings should fall back to defaults when env vars are absent."""
    s = _fresh_settings()
    assert s.app_name == "llm-cost-router"
    assert s.debug is False
    assert "localhost" in s.database_url
    assert "localhost" in s.redis_url


def test_settings_singleton():
    """get_settings() should return the same instance on repeated calls."""
    a = get_settings()
    b = get_settings()
    assert a is b


def test_settings_langfuse_defaults():
    """Langfuse keys default to empty string when not configured."""
    s = _fresh_settings()
    assert s.langfuse_public_key == ""
    assert s.langfuse_secret_key == ""
    assert s.langfuse_host == "https://cloud.langfuse.com"


def test_settings_langsmith_defaults():
    """LangSmith keys default to empty string when not configured."""
    s = _fresh_settings()
    assert s.langchain_api_key == ""
    assert s.langchain_tracing_v2 is True
    assert s.langchain_project == "llm-cost-router"


def test_settings_provider_keys_default_empty():
    """OpenAI and Anthropic keys default to empty string."""
    s = _fresh_settings()
    assert s.openai_api_key == ""
    assert s.anthropic_api_key == ""


def test_settings_env_override():
    """Environment variables override defaults."""
    s = _fresh_settings(APP_NAME="custom-app", DEBUG="true")
    assert s.app_name == "custom-app"
    assert s.debug is True


def test_settings_cors_defaults():
    """CORS defaults: wide-open allowlist, all methods/headers, credentials."""
    s = _fresh_settings()
    assert s.cors_origins == "*"
    assert s.cors_allow_methods == "*"
    assert s.cors_allow_headers == "*"
    assert s.cors_allow_credentials is True


def test_settings_cors_override():
    """CORS values can be set via environment variables."""
    s = _fresh_settings(
        CORS_ORIGINS="https://app.example.com,https://admin.example.com",
        CORS_ALLOW_CREDENTIALS="false",
    )
    assert s.cors_origins == "https://app.example.com,https://admin.example.com"
    assert s.cors_allow_credentials is False
