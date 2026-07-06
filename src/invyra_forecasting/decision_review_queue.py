from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from invyra_forecasting.decision_review import ForecastDecisionReviewPacket


class DecisionReviewQueueStatus(StrEnum):
    """Read-only queue status for forecast review workflow tracking."""

    PENDING_REVIEW = "PENDING_REVIEW"
    NEEDS_MORE_EVIDENCE = "NEEDS_MORE_EVIDENCE"
    READY_FOR_OPERATOR_REVIEW = "READY_FOR_OPERATOR_REVIEW"


@dataclass(frozen=True)
class DecisionReviewQueueItem:
    """A read-only review queue item wrapping a forecast decision packet."""

    queue_id: str
    packet: ForecastDecisionReviewPacket
    status: DecisionReviewQueueStatus
    priority: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "queue_id": self.queue_id,
            "packet": self.packet.to_dict(),
            "status": self.status.value,
            "priority": self.priority,
            "created_at": self.created_at,
            "advisory_only": True,
            "read_only": True,
            "inventory_source_of_truth_preserved": True,
        }


class DecisionReviewQueueBuilder:
    """Builds read-only queue items without approving or changing operational records."""

    def build_item(self, *, queue_id: str, packet: ForecastDecisionReviewPacket) -> DecisionReviewQueueItem:
        status = self._status_for_packet(packet)
        priority = self._priority_for_packet(packet)
        return DecisionReviewQueueItem(
            queue_id=queue_id,
            packet=packet,
            status=status,
            priority=priority,
        )

    def _status_for_packet(self, packet: ForecastDecisionReviewPacket) -> DecisionReviewQueueStatus:
        if packet.decision_ready:
            return DecisionReviewQueueStatus.READY_FOR_OPERATOR_REVIEW
        if packet.packet_has_missing_evidence if hasattr(packet, "packet_has_missing_evidence") else False:
            return DecisionReviewQueueStatus.NEEDS_MORE_EVIDENCE
        if any("evidence reference" in warning for warning in packet.decision_gate.warnings):
            return DecisionReviewQueueStatus.NEEDS_MORE_EVIDENCE
        return DecisionReviewQueueStatus.PENDING_REVIEW

    def _priority_for_packet(self, packet: ForecastDecisionReviewPacket) -> str:
        risk = packet.forecast.stockout_risk.upper()
        if risk == "CRITICAL":
            return "HIGH"
        if risk == "HIGH":
            return "MEDIUM"
        return "NORMAL"
