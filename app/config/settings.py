# ---------------------------------------------------------------------------
# settings.py — Application configuration via Pydantic BaseSettings
# ---------------------------------------------------------------------------
# Loads environment variables from .env (or real env).  Every value has a
# sensible default so the app can start even when the corresponding service
# is not yet configured — health checks will report "down" instead.
# ---------------------------------------------------------------------------

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration object.  Field names match the env-var names
    defined in .env.example so that ``python-dotenv`` picks them up
    automatically."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # -- Application --------------------------------------------------------
    app_name: str = "llm-cost-router"
    debug: bool = False

    # -- PostgreSQL ---------------------------------------------------------
    database_url: str = "postgresql+asyncpg://localhost:5432/llm_cost"

    # -- Redis --------------------------------------------------------------
    redis_url: str = "redis://localhost:6379/0"

    # -- Langfuse (production observability) --------------------------------
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"

    # -- LangSmith (dev / LangGraph debugging) ------------------------------
    langchain_api_key: str = ""
    langchain_tracing_v2: bool = True
    langchain_project: str = "llm-cost-router"

    # -- LLM Providers ------------------------------------------------------
    provider_api_key: str = ""
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    # -- CORS ---------------------------------------------------------------
    # Comma-separated list e.g. "https://a.com,https://b.com" or "*".
    # "*" is only honoured when credentials are disabled (Starlette rule).
    cors_origins: str = "*"
    cors_allow_methods: str = "*"
    cors_allow_headers: str = "*"
    cors_allow_credentials: bool = True

    # -- MCP (Model Context Protocol) ----------------------------------------
    mcp_allowed_tools: str = "search_knowledge,calculate,get_customer"
    mcp_tool_timeout: int = 10
    mcp_injection_extra_patterns: str = ""

    # -- Dashboard -----------------------------------------------------------
    dashboard_port: int = 8501
    api_base_url: str = "http://localhost:8000"


@lru_cache
def get_settings() -> Settings:
    """Return a singleton Settings instance.

    Using ``@lru_cache`` ensures the .env file is read only once, even if
    ``get_settings()`` is called from many places during a single process
    lifetime.
    """
    return Settings()
