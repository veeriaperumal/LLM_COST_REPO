# ---------------------------------------------------------------------------
# router.py — Conditional edge logic for the LangGraph workflow
# ---------------------------------------------------------------------------
# Implements the accept / revise / escalate decision after evaluation.
# ---------------------------------------------------------------------------

from __future__ import annotations

from typing import Any, Literal

from app.graph.state import GraphState


def decide_next(state: GraphState) -> Literal["finalize", "route"]:
    """Return the next node name after the evaluate stage.

    Decision matrix (spec.md:112-115):
      - score >= 0.8            → finalize (accept)
      - moderate + retries left → route    (revise)
      - severe or no retries    → finalize (escalate)
    """
    evaluation = state.get("evaluation", {})
    status = evaluation.get("status", "escalate")

    if status == "accept":
        return "finalize"
    elif status == "revise":
        return "route"
    else:
        return "finalize"
