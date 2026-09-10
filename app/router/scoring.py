# ---------------------------------------------------------------------------
# scoring.py — Fixed weighted routing score and model selection
# ---------------------------------------------------------------------------
# Spec score (line 103-108):
#   Score = 0.45 * Quality + 0.30 * Latency + 0.25 * Cost
#
# Selection returns the highest scoring model; on exact ties the cheapest
# model wins, then the fastest — cost-awareness is honoured only among
# otherwise-equivalent candidates.
# ---------------------------------------------------------------------------

from dataclasses import dataclass
from typing import Sequence

from app.router.schemas import ScoreBreakdown

# Fixed weights from the spec — do not change casually.
W_QUALITY = 0.45
W_LATENCY = 0.30
W_COST = 0.25


@dataclass(frozen=True)
class _Candidate:
    """Normalized metrics plus the raw cost for tie-breaking."""

    model_id: str
    quality: float
    latency_score: float
    cost_score: float
    estimated_cost_usd: float

    @property
    def score(self) -> float:
        return (
            W_QUALITY * self.quality
            + W_LATENCY * self.latency_score
            + W_COST * self.cost_score
        )


def build_scorecards(
    model_ids: Sequence[str],
    qualities: Sequence[float],
    latency_scores: Sequence[float],
    cost_scores: Sequence[float],
    costs_usd: Sequence[float],
) -> dict[str, ScoreBreakdown]:
    """Build a {model_id: ScoreBreakdown} map for the frontier."""
    scorecards: dict[str, ScoreBreakdown] = {}
    for mid, q, ls, cs, cost in zip(
        model_ids, qualities, latency_scores, cost_scores, costs_usd
    ):
        c = _Candidate(mid, q, ls, cs, cost)
        scorecards[mid] = ScoreBreakdown(
            model_id=mid,
            quality=q,
            latency_score=ls,
            cost_score=cs,
            score=round(c.score, 6),
            estimated_cost_usd=cost,
        )
    return scorecards


def select_best(scorecards: dict[str, ScoreBreakdown]) -> str | None:
    """Return the model_id with the highest weighted score.

    Ties are broken by (cheapest first, then fastest latency, then highest
    quality).  Returns None when scorecards is empty.
    """
    if not scorecards:
        return None

    best: ScoreBreakdown | None = None
    for breakdown in scorecards.values():
        if best is None:
            best = breakdown
            continue
        if breakdown.score > best.score:
            best = breakdown
        elif breakdown.score == best.score:
            # Tie-break: cheaper cost
            if breakdown.estimated_cost_usd < best.estimated_cost_usd:
                best = breakdown
            elif breakdown.estimated_cost_usd == best.estimated_cost_usd:
                # Then: faster latency, then higher quality
                if breakdown.latency_score > best.latency_score:
                    best = breakdown
                elif breakdown.latency_score == best.latency_score:
                    if breakdown.quality > best.quality:
                        best = breakdown
    return best.model_id if best else None