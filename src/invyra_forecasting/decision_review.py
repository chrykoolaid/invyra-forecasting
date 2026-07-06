from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from invyra_forecasting.decision_gates import ForecastDecisionGateResult
from invyra_forecasting.models.contracts import ForecastModelOutput


@dataclass(frozen=True)
class ForecastDecisionReviewPacket:
    """Read-only packet for operator review of a forecast decision."""

    forecast: ForecastModelOutput
    decision_gate: ForecastDecisionGateResult
    evidence_summary: tuple[str, ...]
    review_notes: tuple[str, ...] = ()
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def decision_ready(self) -> bool:
        return self.decision_gate.decision_ready

    def to_dict(self) -> dict[str, Any]:
        return {
            "forecast": self.forecast.to_dict(),
            "decision_gate": self.decision_gate.to_dict(),
            "decision_ready": self.decision_ready,
            "evidence_summary": list(self.evidence_summary),
            "review_notes": list(self.review_notes),
            "created_at": self.created_at,
            "advisory_only": True,
            "read_only": True,
            "inventory_source_of_truth_preserved": True,
        }


class ForecastDecisionReviewPacketBuilder:
    """Builds audit-safe forecast review packets without changing system state."""

    def build(
        self,
        *,
        forecast: ForecastModelOutput,
        decision_gate: ForecastDecisionGateResult,
        review_notes: tuple[str, ...] = (),
    ) -> ForecastDecisionReviewPacket:
        evidence_summary = self._summarize_evidence(forecast)
        notes = tuple(review_notes) + (
            "Decision review packet remained advisory-only and read-only; it did not mutate inventory, movements, purchase orders, or ledger truth.",
        )
        return ForecastDecisionReviewPacket(
            forecast=forecast,
            decision_gate=decision_gate,
            evidence_summary=evidence_summary,
            review_notes=notes,
        )

    def _summarize_evidence(self, forecast: ForecastModelOutput) -> tuple[str, ...]:
        evidence_count = len(forecast.evidence_refs)
        if evidence_count == 0:
            return ("No evidence references were attached to this forecast.",)
        return (
            f"Forecast includes {evidence_count} evidence reference(s).",
            f"First evidence reference: {forecast.evidence_refs[0]}",
        )
