# ---------------------------------------------------------------------------
# decision.py — Structured decision-factor logging for the router
# ---------------------------------------------------------------------------
# Every choice the router makes (which models were filtered and why, which
# were dominated, the final score board) is captured twice:
#   1. as a structured dict in the RoutingResult.decision_log
#   2. as an INFO log line via logging.getLogger("app.router")
# ---------------------------------------------------------------------------

import logging
from typing import Any

from app.router.schemas import RoutingRequest, ScoreBreakdown

logger = logging.getLogger("app.router")


class DecisionRecorder:
    """Accumulates structured logs and mirrors them to the standard logger."""

    def __init__(self, request: RoutingRequest) -> None:
        self._request = request
        self._entries: list[dict[str, Any]] = []

    def record(self, stage: str, detail: dict[str, Any]) -> None:
        """Append one decision entry and emit an INFO log line."""
        entry = {
            "stage": stage,
            "detail": detail,
        }
        self._entries.append(entry)
        logger.info("router[%s] %s", stage, detail)

    def record_exclusion(
        self, stage: str, model_id: str, reason: str
    ) -> None:
        """Shortcut for recording a single-model exclusion."""
        self.record(stage, {"excluded": model_id, "reason": reason})

    def record_scores(
        self, scores: dict[str, ScoreBreakdown], selected: str | None
    ) -> None:
        """Record the score board and the winning model."""
        self.record(
            "score",
            {
                "selected": selected,
                "board": {
                    mid: breakdown.model_dump() for mid, breakdown in scores.items()
                },
            },
        )

    @property
    def entries(self) -> list[dict[str, Any]]:
        """The complete structured decision log."""
        return list(self._entries)