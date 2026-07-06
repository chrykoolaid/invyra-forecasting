from __future__ import annotations

from dataclasses import dataclass

from invyra_forecasting.decision_review_queue import DecisionReviewQueueStatus
from invyra_forecasting.decision_review_store import DecisionReviewQueueSnapshot


@dataclass(frozen=True)
class DecisionReviewSummary:
    """Read-only summary of forecast decision review queue state."""

    total_count: int
    ready_count: int
    pending_count: int
    needs_more_evidence_count: int
    high_priority_count: int
    medium_priority_count: int
    normal_priority_count: int

    def to_dict(self) -> dict[str, object]:
        return {
            "total_count": self.total_count,
            "ready_count": self.ready_count,
            "pending_count": self.pending_count,
            "needs_more_evidence_count": self.needs_more_evidence_count,
            "high_priority_count": self.high_priority_count,
            "medium_priority_count": self.medium_priority_count,
            "normal_priority_count": self.normal_priority_count,
            "advisory_only": True,
            "read_only": True,
            "inventory_source_of_truth_preserved": True,
        }


class DecisionReviewSummaryBuilder:
    """Builds read-only queue summaries for presentation and monitoring."""

    def build(self, snapshot: DecisionReviewQueueSnapshot) -> DecisionReviewSummary:
        items = snapshot.items
        return DecisionReviewSummary(
            total_count=len(items),
            ready_count=sum(1 for item in items if item.status == DecisionReviewQueueStatus.READY_FOR_OPERATOR_REVIEW),
            pending_count=sum(1 for item in items if item.status == DecisionReviewQueueStatus.PENDING_REVIEW),
            needs_more_evidence_count=sum(1 for item in items if item.status == DecisionReviewQueueStatus.NEEDS_MORE_EVIDENCE),
            high_priority_count=sum(1 for item in items if item.priority.upper() == "HIGH"),
            medium_priority_count=sum(1 for item in items if item.priority.upper() == "MEDIUM"),
            normal_priority_count=sum(1 for item in items if item.priority.upper() == "NORMAL"),
        )
