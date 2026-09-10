# ---------------------------------------------------------------------------
# test_scoring.py — Tests for weighted scoring and selection
# ---------------------------------------------------------------------------

import pytest

from app.router.scoring import (
    W_COST,
    W_LATENCY,
    W_QUALITY,
    build_scorecards,
    select_best,
)


def test_weight_constants_match_spec():
    """Spec weights: 45% quality, 30% latency, 25% cost."""
    assert W_QUALITY == 0.45
    assert W_LATENCY == 0.30
    assert W_COST == 0.25


def test_score_formula():
    """score = 0.45*q + 0.30*lat + 0.25*cost."""
    scorecards = build_scorecards(
        ["m"], [1.0], [1.0], [1.0], [0.01]
    )
    assert scorecards["m"].score == pytest.approx(1.0)

    scorecards = build_scorecards(
        ["m"], [0.5], [0.5], [0.5], [0.01]
    )
    assert scorecards["m"].score == pytest.approx(0.5)


def test_score_manual_calculation():
    """A hand-computed weighted score."""
    # q=0.8, latency_score=0.6, cost_score=0.4
    expected = 0.45 * 0.8 + 0.30 * 0.6 + 0.25 * 0.4
    scorecards = build_scorecards(
        ["m"], [0.8], [0.6], [0.4], [0.02]
    )
    assert scorecards["m"].score == pytest.approx(expected)


def test_select_best_picks_highest_score():
    scorecards = build_scorecards(
        ["low", "high"],
        [0.5, 0.9],
        [0.5, 0.7],
        [0.5, 0.6],
        [0.02, 0.03],
    )
    assert select_best(scorecards) == "high"


def test_select_best_tie_breaks_to_cheapest():
    """Equal scores → the cheaper model wins."""
    # Identical metrics so both score the same; b is cheaper
    scorecards = build_scorecards(
        ["a", "b"],
        [0.8, 0.8],
        [0.7, 0.7],
        [0.5, 0.5],
        [0.02, 0.005],
    )
    assert scorecards["a"].score == pytest.approx(scorecards["b"].score)
    assert select_best(scorecards) == "b"


def test_select_best_tie_equal_cost_breaks_to_latency():
    """Equal score AND equal cost → faster (higher latency_score) wins."""
    scorecards = build_scorecards(
        ["slow", "fast"],
        [0.8, 0.8],
        [0.6, 0.8],
        [0.5, 0.5],
        [0.02, 0.02],
    )
    assert select_best(scorecards) == "fast"


def test_select_best_empty_returns_none():
    assert select_best({}) is None


def test_build_scorecards_rounds_score():
    """Scores are rounded to 6 decimal places."""
    scorecards = build_scorecards(
        ["m"], [1 / 3], [1 / 3], [1 / 3], [0.01]
    )
    assert scorecards["m"].score == pytest.approx(0.333333, abs=1e-6)