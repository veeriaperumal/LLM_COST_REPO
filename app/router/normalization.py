# ---------------------------------------------------------------------------
# normalization.py — Min-max normalization of latency and cost to [0, 1]
# ---------------------------------------------------------------------------
# Quality (from ModelMetadata.quality_score) is already in [0, 1].  Latency
# and estimated cost must be inverted so that the *best* value maps to 1.0
# and the *worst* maps to 0.0, making all three dimensions comparable for
# the weighted score.
# ---------------------------------------------------------------------------

from typing import Sequence


def _inverse_min_max(values: Sequence[float]) -> list[float]:
    """Map lower-is-better inputs to [0, 1] where best == 1.0.

    ``best / worst`` are the minimum / maximum of the input list.
    When all inputs are equal (or there is a single input) every value
    maps to 1.0 to avoid a division-by-zero.
    """
    if not values:
        return []

    lo = min(values)
    hi = max(values)

    if hi == lo:
        return [1.0] * len(values)

    return [(hi - v) / (hi - lo) for v in values]


def normalize_latency(latencies_ms: Sequence[float]) -> list[float]:
    """Normalize latency scores (higher = worse, best -> 1.0)."""
    return _inverse_min_max(latencies_ms)


def normalize_cost(costs_usd: Sequence[float]) -> list[float]:
    """Normalize cost scores (higher = worse, cheapest -> 1.0)."""
    return _inverse_min_max(costs_usd)