# ---------------------------------------------------------------------------
# tools.py — MCP tool implementations
# ---------------------------------------------------------------------------
# Three simulated tools for the MVP:
#   search_knowledge  — in-memory knowledge-base search
#   calculate         — safe math expression evaluator
#   get_customer      — in-memory customer lookup
#
# All tools are async functions accepting **kwargs so the gateway can
# invoke them uniformly.  Phase 9 may swap these for real service calls.
# ---------------------------------------------------------------------------

from __future__ import annotations

import ast
import operator
import logging
from typing import Any

logger = logging.getLogger(__name__)

# -- Knowledge base (simulated) -----------------------------------------------

_KNOWLEDGE_STORE: list[dict[str, str]] = [
    {
        "title": "Return Policy",
        "content": "Items can be returned within 30 days of purchase with a valid receipt.",
    },
    {
        "title": "Shipping Options",
        "content": "Standard shipping takes 5-7 business days. Express is 1-2 days.",
    },
    {
        "title": "Warranty Information",
        "content": "All products carry a 1-year manufacturer warranty from date of purchase.",
    },
    {
        "title": "Account Recovery",
        "content": "Contact support with your email and last 4 digits of payment method to recover an account.",
    },
    {
        "title": "API Rate Limits",
        "content": "Free tier: 60 requests/minute. Pro tier: 600 requests/minute. Enterprise: unlimited.",
    },
]

# -- Customer store (simulated) ------------------------------------------------

_CUSTOMER_STORE: dict[str, dict[str, Any]] = {
    "C001": {
        "id": "C001",
        "name": "Alice Johnson",
        "tier": "enterprise",
        "preferences": {"language": "en", "notifications": True},
    },
    "C002": {
        "id": "C002",
        "name": "Bob Smith",
        "tier": "pro",
        "preferences": {"language": "en", "notifications": False},
    },
    "C003": {
        "id": "C003",
        "name": "Carol Davis",
        "tier": "free",
        "preferences": {"language": "es", "notifications": True},
    },
}

# -- Safe math evaluator -------------------------------------------------------

_SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _safe_eval(node: ast.AST) -> float:
    """Recursively evaluate an AST node containing only safe math ops."""
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.BinOp) and type(node.op) in _SAFE_OPERATORS:
        left = _safe_eval(node.left)
        right = _safe_eval(node.right)
        return _SAFE_OPERATORS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _SAFE_OPERATORS:
        return _SAFE_OPERATORS[type(node.op)](_safe_eval(node.operand))
    raise ValueError(f"Unsupported expression: {ast.dump(node)}")


# -- Tool functions ------------------------------------------------------------


async def search_knowledge(*, query: str = "", **_kwargs: Any) -> dict[str, Any]:
    """Search the in-memory knowledge base.

    Returns up to 3 results where the query appears (case-insensitive)
    in the title or content.  Relevance is a simple substring-match
    heuristic (1.0 = exact, 0.5 = partial).
    """
    query_lower = query.lower()
    results: list[dict[str, Any]] = []

    for entry in _KNOWLEDGE_STORE:
        title_lower = entry["title"].lower()
        content_lower = entry["content"].lower()

        if query_lower in title_lower:
            relevance = 1.0 if query_lower == title_lower else 0.8
            results.append({**entry, "relevance": relevance})
        elif query_lower in content_lower:
            results.append({**entry, "relevance": 0.5})

        if len(results) >= 3:
            break

    return {"results": results, "query": query, "total": len(results)}


async def calculate(*, expression: str = "", **_kwargs: Any) -> dict[str, Any]:
    """Evaluate a math expression safely.

    Supports: +, -, *, /, //, %, ** and parentheses.  No variable
    assignments, function calls, or imports are allowed.
    """
    try:
        tree = ast.parse(expression.strip(), mode="eval")
        result = _safe_eval(tree)
        return {"result": result, "expression": expression, "error": None}
    except (ValueError, TypeError, ZeroDivisionError, SyntaxError) as exc:
        return {"result": None, "expression": expression, "error": str(exc)}


async def get_customer(*, customer_id: str = "", **_kwargs: Any) -> dict[str, Any]:
    """Look up a customer by ID from the simulated store."""
    customer = _CUSTOMER_STORE.get(customer_id)
    if customer is None:
        return {"error": f"Customer '{customer_id}' not found", "customer": None}
    return {"customer": customer, "customer_id": customer_id}


# -- Tool registry -------------------------------------------------------------

MCP_TOOLS: dict[str, Any] = {
    "search_knowledge": search_knowledge,
    "calculate": calculate,
    "get_customer": get_customer,
}
