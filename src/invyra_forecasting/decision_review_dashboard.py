from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from invyra_forecasting.decision_review_store import DecisionReviewQueueSnapshot
from invyra_forecasting.decision_review_summary import DecisionReviewSummary, DecisionReviewSummaryBuilder


@dataclass(frozen=True)
class DecisionReviewDashboardProjection:
    """Read-only dashboard projection for forecast decision review queues."""

    snapshot: DecisionReviewQueueSnapshot
    summary: DecisionReviewSummary
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary.to_dict(),
            "snapshot": self.snapshot.to_dict(),
            "generated_at": self.generated_at,
            "advisory_only": True,
            "read_only": True,
            "inventory_source_of_truth_preserved": True,
        }


class DecisionReviewDashboardProjectionBuilder:
    """Builds read-only queue dashboard projections for future UI/API use."""

    def __init__(self, summary_builder: DecisionReviewSummaryBuilder | None = None) -> None:
        self._summary_builder = summary_builder or DecisionReviewSummaryBuilder()

    def build(self, snapshot: DecisionReviewQueueSnapshot) -> DecisionReviewDashboardProjection:
        return DecisionReviewDashboardProjection(
            snapshot=snapshot,
            summary=self._summary_builder.build(snapshot),
        )
