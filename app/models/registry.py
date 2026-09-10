# ---------------------------------------------------------------------------
# registry.py — Central model registry
# ---------------------------------------------------------------------------
# Stores ModelMetadata instances and provides query / filter helpers used
# by the router (Phase 3) to find eligible models for a given request.
# ---------------------------------------------------------------------------

from typing import Sequence

from app.models.schemas import ModelMetadata, TaskType


class ModelRegistry:
    """In-memory registry of available LLM models.

    In production this would back onto PostgreSQL, but for Phase 0-1 the
    dict-based approach is sufficient and keeps the code testable without
    database dependencies.
    """

    def __init__(self) -> None:
        self._models: dict[str, ModelMetadata] = {}

    # -- Write operations ---------------------------------------------------

    def register(self, model: ModelMetadata) -> None:
        """Add or overwrite a model in the registry."""
        self._models[model.model_id] = model

    def unregister(self, model_id: str) -> bool:
        """Remove a model.  Returns True if it existed."""
        return self._models.pop(model_id, None) is not None

    # -- Read operations ----------------------------------------------------

    def get(self, model_id: str) -> ModelMetadata | None:
        """Return a single model by ID, or None."""
        return self._models.get(model_id)

    def get_all(self) -> list[ModelMetadata]:
        """Return every registered model."""
        return list(self._models.values())

    def get_by_provider(self, provider: str) -> list[ModelMetadata]:
        """Return all models from a given provider."""
        return [m for m in self._models.values() if m.provider == provider]

    def filter_by_task(self, task: TaskType) -> list[ModelMetadata]:
        """Return models whose capability set includes *task*."""
        return [
            m for m in self._models.values()
            if task in m.capabilities.supported_tasks
        ]

    def filter_by_capability(
        self,
        *,
        require_structured_output: bool = False,
        require_tools: bool = False,
        min_context_tokens: int = 0,
    ) -> list[ModelMetadata]:
        """Return models that satisfy the given capability constraints."""
        results: list[ModelMetadata] = []
        for m in self._models.values():
            caps = m.capabilities
            if require_structured_output and not caps.supports_structured_output:
                continue
            if require_tools and not caps.supports_tools:
                continue
            if caps.max_context_tokens < min_context_tokens:
                continue
            results.append(m)
        return results

    def __len__(self) -> int:
        return len(self._models)
