# Completed Tasks

## Phase 0 — FastAPI Health Endpoints

**Date:** 2026-09-10
**Status:** Done

### Files Created

| File | Description |
|---|---|
| `app/__init__.py` | Empty package marker |
| `app/config/__init__.py` | Empty package marker |
| `app/config/settings.py` | Pydantic `BaseSettings` — loads env vars from `.env` |
| `app/database/__init__.py` | Empty package marker |
| `app/database/connection.py` | PostgreSQL async health check via SQLAlchemy |
| `app/cache/__init__.py` | Empty package marker |
| `app/cache/connection.py` | Redis async health check via `redis.asyncio` |
| `app/observability/__init__.py` | Empty package marker |
| `app/observability/connection.py` | Langfuse + LangSmith connectivity probes via `httpx` |
| `app/api/__init__.py` | Empty package marker |
| `app/api/health.py` | FastAPI router — 4 health endpoints with full comments |
| `app/api/router.py` | Top-level API router aggregation (`/api/v1`) |
| `app/main.py` | FastAPI app entry point — lifespan, CORS, router mounting |
| `tests/__init__.py` | Empty package marker |
| `tests/conftest.py` | Shared pytest fixtures (async test client) |
| `tests/test_health.py` | 10 tests covering all health endpoints |
| `tests/test_settings.py` | 4 tests for config defaults and singleton |
| `tests/test_connections.py` | 12 tests for individual service health checks (mocked) |

### Health Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `GET /health` | GET | Convenience liveness — returns 200 with status ok |
| `GET /health/live` | GET | Liveness probe — process is alive |
| `GET /health/ready` | GET | Readiness probe — checks PostgreSQL, Redis, Langfuse, LangSmith |
| `GET /health/startup` | GET | Startup probe — app finished initialising |

### Test Results

```
26 passed in 0.20s
```

- `tests/test_connections.py` — 12 tests (PostgreSQL, Redis, Langfuse, LangSmith: ok, down, skipped scenarios)
- `tests/test_health.py` — 10 tests (all 4 endpoints, degraded/ok/skipped states, timestamp presence)
- `tests/test_settings.py` — 4 tests (defaults, singleton, Langfuse/LangSmith defaults)

### Dependencies Installed

- `pydantic-settings` — for `BaseSettings` env var loading
- `pytest-asyncio` — for `@pytest.mark.asyncio` async test support

### How to Run

```bash
# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run tests
pytest tests/ -v
```

---

## Phase 1 — Model Abstraction

**Date:** 2026-09-10
**Status:** Done

### Files Created

| File | Description |
|---|---|
| `app/models/__init__.py` | Empty package marker |
| `app/models/schemas.py` | `TaskType`, `PricingInfo`, `CapabilitySet`, `ModelMetadata` Pydantic models |
| `app/models/registry.py` | `ModelRegistry` — register/unregister, get/get_all/get_by_provider, filter_by_task/filter_by_capability |
| `app/models/providers/__init__.py` | Empty package marker |
| `app/models/providers/base.py` | `BaseProvider` ABC + `ProviderResponse` schema |
| `app/models/providers/openai.py` | `OpenAIProvider` concrete adapter (official `openai` SDK) |
| `app/models/providers/anthropic.py` | `AnthropicProvider` concrete adapter (official `anthropic` SDK) |
| `tests/test_schemas.py` | 12 tests for Pydantic models |
| `tests/test_registry.py` | 14 tests for ModelRegistry |
| `tests/test_settings.py` | Updated — 6 tests (fixed env-var isolation with `_fresh_settings`) |

### Modified Files

| File | Change |
|---|---|
| `app/config/settings.py` | Added `openai_api_key`, `anthropic_api_key` fields |
| `.env.example` | Added `OPENAI_API_KEY=`, `ANTHROPIC_API_KEY=` |
| `requirements.txt` | Added `openai`, `anthropic` |

### Key Decisions

- **Quality score** defaults to `0.0` — placeholder until Phase 11 (historical feedback) populates real scores.
- **Provider adapters** use official SDKs (`openai`, `anthropic`) behind the `BaseProvider` ABC.
- **Token counting** uses a `len(text) // 4` heuristic (Phase 0-1 approximation; Phase 6 will refine).

### Test Results

```
58 passed in 0.29s
```

| Suite | Count | Coverage |
|---|---|---|
| `test_connections.py` | 12 | PostgreSQL, Redis, Langfuse, LangSmith health probes |
| `test_health.py` | 10 | All 4 health endpoints + degraded/ok/skipped states |
| `test_registry.py` | 14 | Register/unregister, filters by task/capability/provider |
| `test_schemas.py` | 12 | TaskType, PricingInfo cost calc, CapabilitySet, ModelMetadata validation |
| `test_settings.py` | 6 | Defaults, singleton, env overrides, empty provider keys |

### Dependencies Installed

- `openai` — official OpenAI SDK for `OpenAIProvider`
- `anthropic` — official Anthropic SDK for `AnthropicProvider`
