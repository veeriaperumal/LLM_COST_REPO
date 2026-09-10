# ---------------------------------------------------------------------------
# test_normalization.py — Tests for min-max normalization
# ---------------------------------------------------------------------------

import pytest

from app.router.normalization import normalize_cost, normalize_latency


def test_latency_best_is_1_worst_is_0():
    """Best (lowest) latency maps to 1.0, worst maps to 0.0."""
    result = normalize_latency([900, 500, 200])
    assert result[2] == pytest.approx(1.0)  # 200ms is best
    assert result[0] == pytest.approx(0.0)  # 900ms is worst
    # middle value
    assert result[1] == pytest.approx(400 / 700)


def test_cost_best_is_1_worst_is_0():
    """Cheapest model maps to 1.0, most expensive maps to 0.0."""
    result = normalize_cost([0.01, 0.005, 0.0001])
    assert result[2] == pytest.approx(1.0)
    assert result[0] == pytest.approx(0.0)


def test_single_candidate_normalizes_to_one():
    """A lone candidate is always 'best' → 1.0."""
    assert normalize_latency([500]) == [1.0]
    assert normalize_cost([0.25]) == [1.0]


def test_all_equal_normalizes_to_one():
    """Ties (no spread) must not divide by zero — all become 1.0."""
    assert normalize_latency([100, 100, 100]) == [1.0, 1.0, 1.0]
    assert normalize_cost([0.5, 0.5]) == [1.0, 1.0]


def test_empty_input_returns_empty():
    """No candidates → no scores."""
    assert normalize_latency([]) == []
    assert normalize_cost([]) == []


def test_inverse_ordering_preserved():
    """Normalized values must keep the original ordering (ascending strength)."""
    result = normalize_latency([1000, 800, 300])
    assert result[2] >= result[1] >= result[0]
    assert all(0.0 <= v <= 1.0 for v in result)