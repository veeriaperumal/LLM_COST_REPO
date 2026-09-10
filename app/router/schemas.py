# ---------------------------------------------------------------------------
# schemas.py — Request/response models for the routing engine
# ---------------------------------------------------------------------------
# Defines what the router receives (RoutingRequest), how a model's score is
# reported (ScoreBreakdown), and the full result of a routing decision
# (RoutingResult) which carries every intermediate decision for telemetry
# and the dashboard.
# ---------------------------------------------------------------------------

from typing import Any

from pydantic import BaseModel, Field

from app.models.schemas import TaskType


class RoutingRequest(BaseModel):
    """Everything the router needs to select a model for one request."""

    task: TaskType
    prompt: str = ""
    # Tokens are estimated by the caller (Phase 6).  If missing the engine
    # falls back to a len(text) // 4 heuristic.
    estimated_input_tokens: int | None = Field(
        default=None, ge=0,
        description="Estimated prompt tokens; None triggers a heuristic",
    )
    estimated_output_tokens: int = Field(
        default=256, ge=0,
        description="Expected output tokens used for cost estimation",
    )
    require_structured_output: bool = False
    require_tools: bool = False
    min_context_tokens: int = 0
    # Budget / health constraints (wired to Phase 2 later).
    max_cost_usd: float | None = Field(default=None, ge=0)
    unavailable_models: set[str] = Field(default_factory=set)


class Exclusion(BaseModel):
    """A model dropped at a routing stage, with the reason why."""

    model_id: str
    stage: str = Field(
        ...,
        description="e.g. 'capability', 'budget', 'health', 'pareto'",
    )
    reason: str


class ScoreBreakdown(BaseModel):
    """Per-model normalized metrics and the final weighted score."""

    model_id: str
    quality: float
    latency_score: float
    cost_score: float
    score: float
    estimated_cost_usd: float


class RoutingResult(BaseModel):
    """Full output of one routing decision."""

    request: RoutingRequest
    all_candidates: list[str] = Field(
        default_factory=list, description="Every model in the registry"
    )
    eligible: list[str] = Field(
        default_factory=list,
        description="Models surviving the capability filter",
    )
    exclusions: list[Exclusion] = Field(
        default_factory=list,
        description="Models removed at each stage with reasons",
    )
    pareto_frontier: list[str] = Field(
        default_factory=list,
        description="Undominated models after Pareto filtering",
    )
    scores: dict[str, ScoreBreakdown] = Field(default_factory=dict)
    selected_model: str | None = None
    decision_log: list[dict[str, Any]] = Field(
        default_factory=list, description="Structured decision-factor log"
    )