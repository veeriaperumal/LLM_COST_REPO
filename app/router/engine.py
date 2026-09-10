# ---------------------------------------------------------------------------
# engine.py — The routing engine
# ---------------------------------------------------------------------------
# Orchestrates the Phase 3 pipeline in exactly the order dictated by the
# spec routing method (spec.md:90-94):
#   6. Filter incapable models            (capability filter)
#   7. Apply budget / health constraints  (pluggable)
#   8. Remove dominated models (Pareto)
#   9. Calculate fixed weighted score
#  10. Select model
#
# Phases 2/6 will inject budget and provider-health data; for now the
# engine accepts explicit constraints on RoutingRequest.
# ---------------------------------------------------------------------------

import logging

from app.models.registry import ModelRegistry
from app.models.schemas import TaskType
from app.router.decision import DecisionRecorder
from app.router.normalization import normalize_cost, normalize_latency
from app.router.pareto import pareto_filter
from app.router.schemas import Exclusion, RoutingRequest, RoutingResult
from app.router.scoring import build_scorecards, select_best

logger = logging.getLogger(__name__)


class RoutingError(Exception):
    """Raised when no model can serve the request."""

    def __init__(self, message: str, result: RoutingResult) -> None:
        super().__init__(message)
        self.result = result
        self.message = message


class RouterEngine:
    """Given a ModelRegistry, picks the best eligible model for a request."""

    def __init__(self, registry: ModelRegistry) -> None:
        self._registry = registry

    # -- Main entry point ---------------------------------------------------

    def route(self, request: RoutingRequest) -> RoutingResult:
        """Run the full routing pipeline and return a RoutingResult.

        Raises
        ------
        RoutingError
            When the registry yields no eligible candidates.
        """
        recorder = DecisionRecorder(request)
        result = RoutingResult(request=request)

        # A single token estimate is computed up-front and reused by both
        # the budget check and the cost metric so the two never disagree.
        token_estimate = request.estimated_input_tokens
        if token_estimate is None:
            token_estimate = max(1, len(request.prompt) // 4)

        all_models = self._registry.get_all()
        result.all_candidates = [m.model_id for m in all_models]

        if not all_models:
            raise RoutingError("No models registered", result)

        # -- Step 6: capability filtering -----------------------------------
        eligible, exclusions = self._filter_capabilities(request, all_models)
        result.eligible = [m.model_id for m in eligible]
        result.exclusions.extend(exclusions)
        for e in exclusions:
            recorder.record_exclusion(e.stage, e.model_id, e.reason)
        recorder.record(
            "capability",
            {"eligible": result.eligible, "excluded": len(exclusions)},
        )

        if not eligible:
            self._finalize(result, recorder, selected=None)
            raise RoutingError("No eligible models for this request", result)

        # -- Step 7: budget / health constraints ------------------------------
        constrained, exclusions = self._filter_constraints(
            request, eligible, token_estimate
        )
        result.exclusions.extend(exclusions)
        for e in exclusions:
            recorder.record_exclusion(e.stage, e.model_id, e.reason)

        if not constrained:
            self._finalize(result, recorder, selected=None)
            raise RoutingError("All eligible models rejected by constraints", result)

        # -- Compute per-model metrics ----------------------------------------
        metrics = self._metric_vectors(request, constrained, token_estimate)
        model_ids = list(metrics["model_id"])
        qualities = metrics["quality"]
        latencies = metrics["latency_ms"]
        costs = metrics["cost_usd"]

        # -- Step 8: Pareto filtering -----------------------------------------
        frontier, dominated = pareto_filter(
            model_ids, qualities, latencies, costs
        )
        result.pareto_frontier = frontier
        for mid in dominated:
            ex = Exclusion(
                model_id=mid, stage="pareto",
                reason="dominated by another eligible model",
            )
            result.exclusions.append(ex)
            recorder.record_exclusion("pareto", mid, ex.reason)
        recorder.record(
            "pareto",
            {"frontier": frontier, "dominated": dominated},
        )

        # -- Step 9: normalize + weighted score (frontier only) ----------------
        frontier_set = set(frontier)
        f_ids = [mid for mid in model_ids if mid in frontier_set]
        f_qualities = [q for mid, q in zip(model_ids, qualities) if mid in frontier_set]
        f_latencies = [l for mid, l in zip(model_ids, latencies) if mid in frontier_set]
        f_costs = [c for mid, c in zip(model_ids, costs) if mid in frontier_set]

        latency_scores = normalize_latency(f_latencies)
        cost_scores = normalize_cost(f_costs)
        scorecards = build_scorecards(
            f_ids, f_qualities, latency_scores, cost_scores, f_costs
        )
        result.scores = scorecards

        # -- Step 10: select ----------------------------------------------------
        selected = select_best(scorecards)
        result.selected_model = selected

        self._finalize(result, recorder, selected)
        return result

    # -- Pipeline stages ------------------------------------------------------

    @staticmethod
    def _filter_capabilities(
        request: RoutingRequest, models: list
    ) -> tuple[list, list[Exclusion]]:
        """Keep only models whose capabilities satisfy the request."""
        eligible: list = []
        exclusions: list[Exclusion] = []

        for m in models:
            reasons: list[str] = []
            if request.task not in m.capabilities.supported_tasks:
                reasons.append(f"does not support task '{request.task.value}'")
            if request.require_structured_output and not (
                m.capabilities.supports_structured_output
            ):
                reasons.append("no structured output support")
            if request.require_tools and not m.capabilities.supports_tools:
                reasons.append("no tool-calling support")
            if m.capabilities.max_context_tokens < request.min_context_tokens:
                reasons.append(
                    f"context {m.capabilities.max_context_tokens} < "
                    f"{request.min_context_tokens}"
                )

            if reasons:
                exclusions.append(
                    Exclusion(
                        model_id=m.model_id, stage="capability",
                        reason="; ".join(reasons),
                    )
                )
            else:
                eligible.append(m)

        return eligible, exclusions

    @staticmethod
    def _filter_constraints(
        request: RoutingRequest,
        models: list,
        token_estimate: int,
    ) -> tuple[list, list[Exclusion]]:
        """Apply budget and availability constraints."""
        eligible: list = []
        exclusions: list[Exclusion] = []

        for m in models:
            if m.model_id in request.unavailable_models:
                exclusions.append(
                    Exclusion(
                        model_id=m.model_id, stage="health",
                        reason="marked unavailable",
                    )
                )
                continue
            if request.max_cost_usd is not None:
                estimate = m.pricing.calculate_cost(
                    token_estimate, request.estimated_output_tokens
                )
                if estimate > request.max_cost_usd:
                    exclusions.append(
                        Exclusion(
                            model_id=m.model_id, stage="budget",
                            reason=f"estimated cost ${estimate:.4f} exceeds "
                                   f"budget ${request.max_cost_usd:.4f}",
                        )
                    )
                    continue
            eligible.append(m)

        return eligible, exclusions

    @staticmethod
    def _metric_vectors(
        request: RoutingRequest, models: list, token_estimate: int
    ) -> dict:
        """Return parallel metric vectors (quality, latency, cost) per model."""
        vectors = {
            "model_id": [],
            "quality": [],
            "latency_ms": [],
            "cost_usd": [],
        }
        for m in models:
            vectors["model_id"].append(m.model_id)
            vectors["quality"].append(m.quality_score)
            vectors["latency_ms"].append(m.typical_latency_ms)
            vectors["cost_usd"].append(
                m.pricing.calculate_cost(
                    token_estimate, request.estimated_output_tokens
                )
            )
        return vectors

    @staticmethod
    def _finalize(
        result: RoutingResult,
        recorder: DecisionRecorder,
        selected: str | None,
    ) -> None:
        """Attach the score board and decision log to the result."""
        recorder.record_scores(result.scores, selected)
        result.decision_log = recorder.entries


def default_engine() -> RouterEngine:
    """Build a RouterEngine over the seed catalog.

    Imported lazily so that tests can build engines with custom registries
    without triggering catalog construction.
    """
    from app.models.catalog import build_default_registry

    return RouterEngine(build_default_registry())