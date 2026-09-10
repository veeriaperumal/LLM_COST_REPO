# ---------------------------------------------------------------------------
# pareto.py — Pareto dominance filtering
# ---------------------------------------------------------------------------
# A candidate model A dominates B when A is at least as good on *every*
# objective and strictly better on at least one.  Objectives here are:
#   quality  (higher is better)
#   latency  (lower is better)
#   cost     (lower is better)
#
# Models that are dominated by any other candidate are removed; the caller
# is left with the Pareto frontier of undominated models.
# ---------------------------------------------------------------------------

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class _Point:
    """Internal tuple of the three objectives for one candidate."""

    model_id: str
    quality: float
    latency: float
    cost: float


def _dominates(a: _Point, b: _Point) -> bool:
    """Return True when *a* is at least as good as *b* everywhere and
    strictly better in at least one objective."""
    at_least_as_good = (
        a.quality >= b.quality and a.latency <= b.latency and a.cost <= b.cost
    )
    strictly_better = (
        a.quality > b.quality or a.latency < b.latency or a.cost < b.cost
    )
    return at_least_as_good and strictly_better


def pareto_filter(
    model_ids: Sequence[str],
    qualities: Sequence[float],
    latencies_ms: Sequence[float],
    costs_usd: Sequence[float],
) -> tuple[list[str], list[str]]:
    """Remove dominated models.

    Parameters
    ----------
    model_ids, qualities, latencies_ms, costs_usd:
        Parallel sequences describing each candidate.

    Returns
    -------
    (frontier_ids, dominated_ids):
        ``frontier_ids`` are the undominated models; ``dominated_ids`` lists
        every removed model.  Exact ties are kept on both sides (neither
        dominates the other).
    """
    if not model_ids:
        return [], []

    points = [
        _Point(mid, q, l, c)
        for mid, q, l, c in zip(model_ids, qualities, latencies_ms, costs_usd)
    ]

    frontier: list[str] = []
    dominated: list[str] = []

    for candidate in points:
        # A candidate is dominated if *any* other point beats it.
        if any(
            other.model_id != candidate.model_id
            and _dominates(other, candidate)
            for other in points
        ):
            dominated.append(candidate.model_id)
        else:
            frontier.append(candidate.model_id)

    return frontier, dominated