# ---------------------------------------------------------------------------
# mock_data.py — Demo data for dashboard pages
# ---------------------------------------------------------------------------
# Provides realistic fallback data when the FastAPI server is not running
# or when pages depend on unimplemented phases (PostgreSQL, Evaluation).
# ---------------------------------------------------------------------------

from __future__ import annotations

import random
from datetime import datetime, timezone, timedelta

# -- Model catalog (matches app/models/catalog.py) ----------------------------

MOCK_MODELS = [
    {
        "model_id": "gpt-4o",
        "provider": "openai",
        "capabilities": {
            "supported_tasks": ["classification", "extraction", "summarisation", "qa"],
            "supports_structured_output": True,
            "supports_tools": True,
            "max_context_tokens": 128000,
        },
        "pricing": {"input_per_1k": 0.0025, "output_per_1k": 0.010},
        "quality_score": 0.0,
        "typical_latency_ms": 800.0,
    },
    {
        "model_id": "gpt-4o-mini",
        "provider": "openai",
        "capabilities": {
            "supported_tasks": ["classification", "qa"],
            "supports_structured_output": True,
            "supports_tools": False,
            "max_context_tokens": 128000,
        },
        "pricing": {"input_per_1k": 0.00015, "output_per_1k": 0.0006},
        "quality_score": 0.0,
        "typical_latency_ms": 400.0,
    },
    {
        "model_id": "claude-3-5-sonnet",
        "provider": "anthropic",
        "capabilities": {
            "supported_tasks": ["classification", "extraction", "summarisation", "qa"],
            "supports_structured_output": True,
            "supports_tools": True,
            "max_context_tokens": 200000,
        },
        "pricing": {"input_per_1k": 0.003, "output_per_1k": 0.015},
        "quality_score": 0.0,
        "typical_latency_ms": 1200.0,
    },
    {
        "model_id": "claude-haiku-4-5",
        "provider": "anthropic",
        "capabilities": {
            "supported_tasks": ["classification"],
            "supports_structured_output": False,
            "supports_tools": False,
            "max_context_tokens": 200000,
        },
        "pricing": {"input_per_1k": 0.0008, "output_per_1k": 0.004},
        "quality_score": 0.0,
        "typical_latency_ms": 350.0,
    },
]

# -- Request history (mock for Request Explorer) -------------------------------

_TASK_TYPES = ["classification", "extraction", "summarisation", "qa"]
_MODEL_IDS = ["gpt-4o", "gpt-4o-mini", "claude-3-5-sonnet", "claude-haiku-4-5"]
_STATUSES = ["accept", "revise", "escalate"]
_STAGES = ["analyze", "filter", "route", "execute", "evaluate", "finalize"]


def _generate_request_history(count: int = 15) -> list[dict]:
    """Generate realistic mock request history."""
    history = []
    now = datetime.now(timezone.utc)
    prompts = [
        "Classify this customer review as positive or negative",
        "Extract all email addresses from this document",
        "Summarise the following article in 3 sentences",
        "What is the return policy for electronics?",
        "Classify this support ticket by urgency level",
        "Extract key entities from this contract clause",
        "Summarise meeting notes and action items",
        "Explain the difference between TCP and UDP",
        "Is this transaction fraudulent? Analyze the pattern",
        "Summarise the quarterly earnings report",
        "Extract product names and prices from this page",
        "Classify this email as spam or not spam",
        "What are the shipping options available?",
        "Summarise customer feedback from this survey",
        "Extract dates and amounts from this invoice",
    ]

    for i in range(count):
        selected = random.choice(_MODEL_IDS)
        task = random.choice(_TASK_TYPES)
        status = random.choices(_STATUSES, weights=[0.7, 0.2, 0.1])[0]
        cost = round(random.uniform(0.0001, 0.01), 4)
        latency = round(random.uniform(200, 1500), 1)
        score = round(random.uniform(0.5, 1.0), 2)
        ts = now - timedelta(hours=random.randint(0, 72), minutes=random.randint(0, 59))

        history.append({
            "request_id": f"req-{i+1:04d}",
            "timestamp": ts.isoformat(),
            "task": task,
            "prompt": prompts[i % len(prompts)],
            "selected_model": selected,
            "provider": "openai" if "gpt" in selected else "anthropic",
            "status": status,
            "evaluation_score": score,
            "cost_usd": cost,
            "latency_ms": latency,
            "input_tokens": random.randint(50, 500),
            "output_tokens": random.randint(20, 300),
            "retry_count": 0 if status == "accept" else random.randint(0, 2),
            "stages_completed": _STAGES[:4 + random.randint(0, 2)],
        })
    return sorted(history, key=lambda x: x["timestamp"], reverse=True)


MOCK_REQUEST_HISTORY = _generate_request_history()

# -- Evaluation results (mock for Evaluation Lab) -----------------------------

MOCK_EVALUATION_RESULTS = [
    {
        "dataset": "sentiment-analysis-v1",
        "examples": 20,
        "router_accuracy": 0.92,
        "strongest_accuracy": 0.97,
        "cheapest_accuracy": 0.71,
        "router_avg_cost": 0.0018,
        "strongest_avg_cost": 0.0085,
        "cheapest_avg_cost": 0.0004,
        "savings_vs_strongest": 0.34,
        "router_avg_latency_ms": 620,
        "strongest_avg_latency_ms": 980,
        "cheapest_avg_latency_ms": 370,
    },
    {
        "dataset": "entity-extraction-v1",
        "examples": 22,
        "router_accuracy": 0.88,
        "strongest_accuracy": 0.95,
        "cheapest_accuracy": 0.65,
        "router_avg_cost": 0.0022,
        "strongest_avg_cost": 0.011,
        "cheapest_avg_cost": 0.0005,
        "savings_vs_strongest": 0.40,
        "router_avg_latency_ms": 750,
        "strongest_avg_latency_ms": 1100,
        "cheapest_avg_latency_ms": 380,
    },
    {
        "dataset": "qa-benchmark-v1",
        "examples": 25,
        "router_accuracy": 0.90,
        "strongest_accuracy": 0.96,
        "cheapest_accuracy": 0.73,
        "router_avg_cost": 0.0030,
        "strongest_avg_cost": 0.012,
        "cheapest_avg_cost": 0.0006,
        "savings_vs_strongest": 0.38,
        "router_avg_latency_ms": 680,
        "strongest_avg_latency_ms": 1050,
        "cheapest_avg_latency_ms": 410,
    },
]

MOCK_EVALUATION_EXAMPLES = [
    {"id": 1, "input": "I love this product!", "expected": "positive", "router_output": "positive", "router_model": "gpt-4o-mini", "correct": True},
    {"id": 2, "input": "Terrible experience, never buying again", "expected": "negative", "router_output": "negative", "router_model": "gpt-4o-mini", "correct": True},
    {"id": 3, "input": "The item arrived on time and works as described", "expected": "positive", "router_output": "positive", "router_model": "gpt-4o-mini", "correct": True},
    {"id": 4, "input": "Broken on arrival, very disappointed", "expected": "negative", "router_output": "negative", "router_model": "gpt-4o", "correct": True},
    {"id": 5, "input": "It's okay, nothing special", "expected": "neutral", "router_output": "neutral", "router_model": "gpt-4o-mini", "correct": True},
    {"id": 6, "input": "Absolutely fantastic service!", "expected": "positive", "router_output": "positive", "router_model": "gpt-4o-mini", "correct": True},
    {"id": 7, "input": "Would not recommend to anyone", "expected": "negative", "router_output": "negative", "router_model": "claude-haiku-4-5", "correct": True},
    {"id": 8, "input": "Exceeded all my expectations", "expected": "positive", "router_output": "positive", "router_model": "gpt-4o-mini", "correct": True},
]

# -- MCP audit entries (mock for Observability) -------------------------------

_TOOLS = ["search_knowledge", "calculate", "get_customer"]
_TENANTS = ["tenant-alpha", "tenant-beta", "tenant-gamma", "default"]


def _generate_audit_entries(count: int = 25) -> list[dict]:
    entries = []
    now = datetime.now(timezone.utc)
    for i in range(count):
        ts = now - timedelta(hours=random.randint(0, 48), minutes=random.randint(0, 59))
        success = random.random() > 0.08
        entries.append({
            "tool_name": random.choice(_TOOLS),
            "tenant_id": random.choice(_TENANTS),
            "success": success,
            "error": None if success else random.choice(["timeout", "injection detected", "permission denied"]),
            "latency_ms": round(random.uniform(5, 200), 1),
            "timestamp": ts.isoformat(),
        })
    return sorted(entries, key=lambda x: x["timestamp"], reverse=True)


MOCK_AUDIT_ENTRIES = _generate_audit_entries()

# -- Latency distribution (mock) ----------------------------------------------

MOCK_LATENCY_DISTRIBUTION = {
    "p50": 580.0,
    "p95": 1120.0,
    "p99": 1450.0,
    "min": 180.0,
    "max": 1800.0,
}

# -- Model usage counters (mock) ----------------------------------------------

MOCK_MODEL_USAGE = {
    "gpt-4o": 45,
    "gpt-4o-mini": 120,
    "claude-3-5-sonnet": 30,
    "claude-haiku-4-5": 55,
}

# -- Routing decision breakdown (mock) ----------------------------------------

MOCK_ROUTING_DECISIONS = {
    "accept": 160,
    "revise": 30,
    "escalate": 10,
}

# -- Health status (mock fallback) --------------------------------------------

MOCK_HEALTH = {
    "status": "ok",
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "services": {
        "postgres": {"status": "skipped", "message": "not configured"},
        "redis": {"status": "skipped", "message": "not configured"},
        "langfuse": {"status": "skipped", "message": "not configured"},
        "langsmith": {"status": "skipped", "message": "not configured"},
    },
}
