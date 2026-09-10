# ---------------------------------------------------------------------------
# test_pareto.py — Tests for Pareto dominance filtering
# ---------------------------------------------------------------------------

from app.router.pareto import pareto_filter


def test_removes_dominated_model():
    """A model worse on every axis is dominated and removed."""
    # premium beats a on quality, latency, cost
    frontier, dominated = pareto_filter(
        ["premium", "weak"],
        [0.95, 0.40],
        [500, 900],
        [0.01, 0.05],
    )
    assert frontier == ["premium"]
    assert dominated == ["weak"]


def test_keeps_mutually_non_dominated():
    """Models with different trade-offs stay on the frontier."""
    # A: best quality; B: best latency; C: cheapest
    frontier, dominated = pareto_filter(
        ["a", "b", "c"],
        [0.95, 0.80, 0.70],
        [900, 200, 350],
        [0.03, 0.02, 0.001],
    )
    assert set(frontier) == {"a", "b", "c"}
    assert dominated == []


def test_exact_tie_is_not_dominated():
    """Two identical models do not dominate each other → both kept."""
    frontier, dominated = pareto_filter(
        ["x", "y"],
        [0.8, 0.8],
        [500, 500],
        [0.02, 0.02],
    )
    assert set(frontier) == {"x", "y"}
    assert dominated == []


def test_empty_input():
    """Empty input yields empty output."""
    assert pareto_filter([], [], [], []) == ([], [])


def test_single_candidate():
    """A single candidate is its own frontier."""
    frontier, dominated = pareto_filter(["only"], [0.5], [100], [0.01])
    assert frontier == ["only"]
    assert dominated == []


def test_no_dominance_when_worse_on_one_axis():
    """Improving one objective while being worse on another means neither
    candidate dominates the other."""
    # a: better quality, but slower and pricier; b: the opposite
    frontier, dominated = pareto_filter(
        ["a", "b"],
        [0.9, 0.8],
        [500, 400],
        [0.03, 0.02],
    )
    assert set(frontier) == {"a", "b"}
    assert dominated == []


def test_transitive_domination():
    """Best dominates mid which dominates worst — only best survives."""
    frontier, dominated = pareto_filter(
        ["best", "mid", "worst"],
        [0.99, 0.80, 0.60],
        [300, 600, 900],
        [0.001, 0.01, 0.03],
    )
    assert frontier == ["best"]
    assert dominated == ["mid", "worst"]