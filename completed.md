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

---

## Phase 3 — Router

**Date:** 2026-09-10
**Status:** Done

### Files Created

| File | Description |
|---|---|
| `app/router/__init__.py` | Empty package marker |
| `app/router/schemas.py` | `RoutingRequest`, `Exclusion`, `ScoreBreakdown`, `RoutingResult` |
| `app/router/normalization.py` | Min-max normalize latency + cost to [0,1] (best → 1.0) |
| `app/router/pareto.py` | `pareto_filter()` — removes dominated models, returns frontier |
| `app/router/scoring.py` | Weighted score `0.45q + 0.30lat + 0.25cost`, `select_best()` + tie-breaks |
| `app/router/decision.py` | `DecisionRecorder` — structured + `logging` decision-factor log |
| `app/router/engine.py` | `RouterEngine` pipeline, `RoutingError`, `default_engine()` |
| `app/models/catalog.py` | Seed catalog — 4 models (gpt-4o, gpt-4o-mini, claude-sonnet, claude-haiku) |

### Test Files Created

| File | Count | Coverage |
|---|---|---|
| `tests/test_normalization.py` | 6 | Best→1/worst→0, single candidate, ties, empty, ordering |
| `tests/test_pareto.py` | 7 | Dominance, non-dominated trade-offs, ties, transitivity, empty/single |
| `tests/test_scoring.py` | 8 | Weights match spec, formula, selection, cost/latency tie-breaks, empty |
| `tests/test_router_engine.py` | 15 | End-to-end pipeline, filters, budget/health, pareto, decision log, errors, catalog |

### Pipeline (spec steps 6–10, `engine.py`)

1. **Capability filter** — task type, structured output, tools, min context (reasoned exclusions)
2. **Constraint filter** — `max_cost_usd` (budget) + `unavailable_models` (health)
3. **Pareto filter** — dominates on quality↑/latency↓/cost↓; frontier kept
4. **Normalize (frontier only)** — min-max inverse so best latency/cost = 1.0
5. **Score + select** — weighted score, tie-break → cheaper → faster → higher quality

Every stage is recorded in `RoutingResult.decision_log` (structured) and echoed via `logging.getLogger("app.router")`.

### Test Results

```
95 passed in 0.66s
```

| Suite | Count | Coverage |
|---|---|---|
| `test_connections.py` | 12 | PostgreSQL, Redis, Langfuse, LangSmith health probes |
| `test_health.py` | 10 | All 4 health endpoints + degraded/ok/skipped states |
| `test_normalization.py` | 6 | Min-max latency/cost normalization |
| `test_pareto.py` | 7 | Dominance filtering and edge cases |
| `test_registry.py` | 14 | Register/unregister, filters by task/capability/provider |
| `test_router_engine.py` | 15 | Full routing pipeline end-to-end |
| `test_schemas.py` | 12 | TaskType, PricingInfo, CapabilitySet, ModelMetadata |
| `test_scoring.py` | 8 | Weighted scoring + selection + tie-breaks |
| `test_settings.py` | 6 | Defaults, singleton, env overrides |

### Notes

- Budget (`max_cost_usd`) and health (`unavailable_models`) are request-level hooks; Phase 2 will wire live budget counters and provider health.
- Quality scores remain `0.0` in the seed catalog until Phase 11 populates them from historical feedback.
- Estimated cost uses token estimates on `RoutingRequest` (fallback `len(prompt)//4`); Phase 6 refines token accounting.

## Phase 4 — Middleware, Response Envelope, Error Handling, CORS

**Date:** 2026-09-10
**Status:** Done

### Scope Decisions (user-confirmed)

- Response envelope applies to **errors + new business endpoints**; `/health` stays raw JSON for k8s/load-balancer conventions.
- `POST /api/v1/route` demo endpoint added to expose `RouterEngine` via the envelope.
- Health endpoints consolidated into a **single** `GET /health` (removed `/health/live`, `/health/ready`, `/health/startup`, and `mark_startup_complete()`).

### Files Created

| File | Description |
|---|---|
| `app/api/context.py` | `RequestContext` dataclass + contextvars helpers (`get_request_id` / `get_correlation_id`) |
| `app/api/schemas.py` | `ApiMeta`, `ApiError`, `ApiResponse` envelope + `ok()` / `fail()` builders |
| `app/api/exceptions.py` | `AppError` hierarchy + `register_exception_handlers(app)` |
| `app/api/middleware.py` | Pure-ASGI `RequestContextMiddleware`, `RequestLoggingMiddleware`, `configure_cors(app)` |
| `app/api/route.py` | `POST /api/v1/route` endpoint (wraps `default_engine()`) |
| `tests/test_middleware.py` | 5 tests — ID headers, correlation honouring, request-id rotation, envelope meta↔header, log line |
| `tests/test_api_schemas.py` | 4 tests — `ok()`/`fail()` envelope shapes, empty request_id outside a request |
| `tests/test_exceptions.py` | 7 tests — AppError codes, custom overrides, 422/404/500 envelopes, RoutingError→400 |
| `tests/test_cors.py` | 4 tests — preflight, allowed/denied origins, wildcard degrades credentials |
| `tests/test_api_route.py` | 3 tests — success envelope, tools constraint, budget-low 429 |

### Files Modified

| File | Change |
|---|---|
| `app/config/settings.py` | Added `cors_origins`, `cors_allow_methods`, `cors_allow_headers`, `cors_allow_credentials` |
| `.env.example` | Added `CORS_ORIGINS`, `CORS_ALLOW_METHODS`, `CORS_ALLOW_HEADERS`, `CORS_ALLOW_CREDENTIALS` |
| `app/api/health.py` | Rewritten to a single consolidated `GET /health` (service checks, 200 ok / 503 degraded) |
| `app/api/router.py` | Now aggregates `health_router` + `route_router` under `/api/v1` |
| `app/main.py` | Middleware wiring, `register_exception_handlers`, routers; empty lifespan |
| `tests/conftest.py` | Dropped `mark_startup_complete`; `ASGITransport(raise_app_exceptions=False)` |
| `tests/test_health.py` | Rewritten to 3 tests for the single endpoint |
| `tests/test_settings.py` | Added CORS filter + 2 CORS tests |

### Key Design Points

- **Middleware ordering** (Starlette: last added runs first): `CORS → request-context → request-logging → route`.
- Middleware is **pure ASGI** (not `BaseHTTPMiddleware`) — the latter re-raises exceptions already handled by FastAPI's exception handlers and leaks contextvars into task groups, breaking both the envelope and request-ID propagation.
- **Two distinct `HTTPException` classes** exist: `starlette.exceptions.HTTPException` (raised by the router for 404s) and `fastapi.exceptions.HTTPException`. Register the handler against *both* or 404s fall back to FastAPI's flat `{"detail": ...}` body.
- `ServerErrorMiddleware` (generic-500 handler) runs **outside** the request-context middleware and always re-raises after sending; the handler therefore falls back to IDs stashed on `scope["state"]` and the ASGI test client must use `raise_app_exceptions=False`.
- Error codes: `VALIDATION_ERROR` (422), `HTTP_ERROR` (404 etc.), `INTERNAL_ERROR` (500, message masked unless `debug=True`), plus AppError subclasses above.
- X-Request-ID / X-Correlation-ID minted per request (inbound correlation honoured) and echoed on responses.

### Test Results

```
112 passed in 0.24s
```

### Notes

- Debugged two failures empirically (`HTTPException` class mismatch → register both; `ServerErrorMiddleware` re-raise → `raise_app_exceptions=False` on the transport).
- `.env` is still populated by the user; only `.env.example` carries the new CORS keys.
