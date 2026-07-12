from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from invyra_forecasting.api.tenant_namespace import current_namespace


@dataclass(frozen=True)
class ForecastReviewContext:
    """Immutable, read-only context associated with one forecast review."""

    review_id: str
    forecast_id: str
    evidence_refs: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    advisory_only: bool = True
    read_only: bool = True
    inventory_source_of_truth_preserved: bool = True

    def __post_init__(self) -> None:
        if not self.review_id:
            raise ValueError("review_id is required")
        if not self.forecast_id:
            raise ValueError("forecast_id is required")
        if not self.advisory_only:
            raise ValueError("review context must remain advisory-only")
        if not self.read_only:
            raise ValueError("review context must remain read-only")
        if not self.inventory_source_of_truth_preserved:
            raise ValueError("inventory source of truth must be preserved")


class InMemoryForecastReviewContextRepository:
    """Request-namespace-isolated storage for temporary review context."""

    def __init__(self) -> None:
        self._contexts_by_namespace: dict[str, dict[str, ForecastReviewContext]] = {}

    def _contexts(self) -> dict[str, ForecastReviewContext]:
        return self._contexts_by_namespace.setdefault(current_namespace(), {})

    def save(self, context: ForecastReviewContext) -> ForecastReviewContext:
        contexts = self._contexts()
        if context.review_id in contexts:
            raise ValueError(f"review context already exists: {context.review_id}")
        contexts[context.review_id] = context
        return context

    def get(self, review_id: str) -> ForecastReviewContext | None:
        return self._contexts().get(review_id)

    def all(self) -> tuple[ForecastReviewContext, ...]:
        return tuple(self._contexts().values())

    def exists(self, review_id: str) -> bool:
        return review_id in self._contexts()
