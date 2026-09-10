# SPEC-001 — Cost-Aware Multi-Model AI Router

## Background

Modern LLM applications face a three-way optimization problem: quality, latency, and cost. The proposed system is a production-style LLM Gateway that intelligently routes each request to the cheapest eligible model while maintaining a configurable quality target.

The system accepts classification, extraction, summarisation, and Q&A requests through a FastAPI gateway and exposes an interactive Streamlit dashboard.

The key principle is: never select a model purely because it is cheap. First determine whether the model can satisfy the request; then optimize cost, latency, and quality among eligible candidates.

LangGraph provides stateful orchestration and persistence, MCP provides standardized tool access, Langfuse provides production LLM observability/evaluation/cost analysis, and LangSmith provides LangGraph development/debugging.

## Requirements

### Must Have

- FastAPI REST gateway.
- Streamlit dashboard.
- Multi-model provider abstraction.
- Classification, extraction, summarisation, and Q&A.
- Capability filtering before routing.
- Pareto filtering.
- Fixed weighted score:
  - Quality: 45%
  - Latency: 30%
  - Cost: 25%.
- Automatic quality-based escalation.
- Hybrid deterministic + LLM evaluation.
- ≥20 held-out evaluation examples.
- LangGraph orchestration.
- MCP tools:
  - search_knowledge
  - calculate
  - get_customer.
- MCP allowlist and per-tool permissions.
- Prompt-injection defenses.
- PostgreSQL persistence.
- Redis runtime state.
- Semantic cache.
- Provider-agnostic prompt-cache abstraction.
- Per-request and global budgets.
- Idempotency.
- Bounded exponential retries.
- Capability-aware provider failover.
- Langfuse production observability.
- LangSmith development/debugging.
- Configurable redaction and retention.
- Tenant-specific policies, budgets, tools, models, and retention.
- Dashboard metrics for cost, savings, quality, latency, escalation, and model usage.

### Should Have

- Historical model-performance feedback.
- Model health scoring.
- Cache savings metrics.
- Prompt-cache savings.
- Evaluation regression testing.
- Streaming.
- Request replay.

### Could Have

- Learned routing.
- Automatic weight optimization.
- A/B routing experiments.
- Human approval for high-risk tools.
- Additional MCP servers.

### Won't Have in MVP

- Kubernetes deployment.
- Full OAuth/RBAC.
- Autonomous model training.
- Arbitrary code execution.
- Full autonomous agent behavior.

## Method

### Architecture

The system consists of Streamlit, FastAPI, LangGraph, the model router, PostgreSQL, Redis, MCP services, Langfuse, and LangSmith.

### Routing

1. Authenticate tenant.
2. Check idempotency.
3. Check exact and semantic caches.
4. Analyze task.
5. Determine tool/context/structured-output requirements.
6. Filter incapable models.
7. Apply budget and provider-health constraints.
8. Remove dominated models using Pareto filtering.
9. Calculate fixed weighted score.
10. Select model.
11. Execute.
12. Evaluate response.
13. Accept, revise, or escalate.
14. Record telemetry and cost.
15. Return response.

### Routing score

```text
Score =
    0.45 × Quality
  + 0.30 × Latency
  + 0.25 × Cost
```

### Quality recovery

- ≥ target: accept.
- Moderate failure: revise once.
- Severe failure: escalate.
- Failed revision: escalate.

### Budget recovery

- If budget allows: normal routing.
- If constrained: select a cheaper eligible model.
- If no model satisfies policy: reject.

### MCP

MCP tools are accessed through a controlled gateway that performs:

- allowlist verification
- tenant permission verification
- schema validation
- prompt-injection checks
- timeout
- audit logging

### Persistence

PostgreSQL stores application state, routing decisions, budget records, evaluation results, and audit metadata.

Redis stores idempotency state, cache data, rate limits, budget counters, and transient model-health information.

Langfuse stores detailed LLM observability/evaluation telemetry.

LangSmith stores LangGraph development/debugging traces.

## Implementation

### Phase 0 — Repository and architecture

Create the project structure, interfaces, configuration system, and local development environment.

### Phase 1 — Model abstraction

Implement provider adapters, model registry, pricing registry, and capability registry.

### Phase 2 — Data infrastructure

Implement PostgreSQL migrations, repositories, Redis integration, idempotency, cache, and budget counters.

### Phase 3 — Router

Implement capability filtering, normalization, Pareto filtering, weighted scoring, and decision-factor logging.

### Phase 4 — LangGraph

Implement the state machine:

```text
START
→ analyze
→ filter
→ route
→ execute
→ evaluate
→ accept/revise/escalate
→ finalize
```

Use persistent checkpoints.

### Phase 5 — MCP

Implement knowledge search, calculator, and customer lookup MCP tools plus authorization and validation.

### Phase 6 — Cost optimization

Implement exact caching, semantic caching, prompt-cache abstraction, token accounting, pricing calculation, and savings calculation.

### Phase 7 — Evaluation

Build the ≥20-example held-out dataset and deterministic/LLM-judge evaluation framework.

Compare:

- strongest model
- cheapest model
- router.

### Phase 8 — Observability

Integrate Langfuse for production traces/evals/cost and LangSmith for LangGraph debugging.

### Phase 9 — Security

Implement API-key hashing, tenant isolation, tool authorization, input validation, redaction, retention, and prompt-injection defenses.

### Phase 10 — Dashboard

Build Overview, Live Router, Request Explorer, Model Comparison, Evaluation Lab, and Observability pages.

### Phase 11 — Historical feedback

Calculate rolling model quality, latency, failure, and tool-success statistics and feed these into model metadata.

### Phase 12 — Final evaluation

Benchmark the router against strongest-model and cheapest-model baselines.

## Milestones

| Milestone | Phase | Deliverable |
|---|---|---|
| M1 | 0 | Project skeleton |
| M2 | 1 | Model abstraction |
| M3 | 2 | PostgreSQL + Redis |
| M4 | 3 | Router |
| M5 | 4 | LangGraph workflow |
| M6 | 5 | MCP integration |
| M7 | 6 | Cost optimization |
| M8 | 7 | Evaluation |
| M9 | 8 | Observability |
| M10 | 9 | Security |
| M11 | 10 | Dashboard |
| M12 | 11 | Feedback loop |
| M13 | 12 | Final benchmark |

## Gathering Results

The final evaluation must report:

- Router accuracy.
- Strongest-model accuracy.
- Cheapest-model accuracy.
- Cost per request.
- Total cost.
- Baseline cost.
- Savings percentage.
- P50/P95/P99 latency.
- Escalation rate.
- Model utilization.
- Cache hit rate.
- Tokens avoided.
- Provider failure rate.
- Retry rate.
- MCP tool success rate.
- Unauthorized tool calls.

Initial engineering targets:

```text
Router quality ≥ 90% of strongest-model baseline
Cost reduction ≥ 30%
Held-out dataset ≥ 20 examples
Unauthorized tool calls = 0
```

These are targets to validate experimentally, not assumed outcomes.

## Need Professional Help in Developing Your Architecture?

Please contact me at [sammuti.com](https://sammuti.com) :)