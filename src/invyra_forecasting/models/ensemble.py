from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Iterable

from invyra_forecasting.models.contracts import ForecastModelOutput


@dataclass(frozen=True)
class EnsembleMemberForecast:
    """One advisory model forecast participating in an ensemble blend."""

    model_id: str
    output: ForecastModelOutput
    weight: float
    rationale: tuple[str, ...] = ()

    def normalized_weight(self, total_weight: float) -> float:
        if total_weight <= 0:
            raise ValueError("Ensemble member weights must contain at least one positive value")
        return max(0.0, float(self.weight)) / total_weight

    def to_dict(self) -> dict[str, object]:
        return {
            "model_id": self.model_id,
            "output": self.output.to_dict(),
            "weight": self.weight,
            "rationale": list(self.rationale),
        }


@dataclass(frozen=True)
class EnsembleForecastAuditRecord:
    """Audit-safe record of an ensemble forecast decision."""

    strategy: str
    member_count: int
    member_weights: dict[str, float]
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, object]:
        return {
            "strategy": self.strategy,
            "member_count": self.member_count,
            "member_weights": dict(self.member_weights),
            "created_at": self.created_at,
            "advisory_only": True,
            "read_only": True,
            "inventory_source_of_truth_preserved": True,
        }


@dataclass(frozen=True)
class EnsembleForecastResult:
    """Blended advisory forecast with transparent member evidence."""

    output: ForecastModelOutput
    members: tuple[EnsembleMemberForecast, ...]
    strategy: str
    audit_record: EnsembleForecastAuditRecord
    explanation: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "output": self.output.to_dict(),
            "members": [member.to_dict() for member in self.members],
            "strategy": self.strategy,
            "audit_record": self.audit_record.to_dict(),
            "explanation": list(self.explanation),
        }


class WeightedAverageEnsembleForecaster:
    """Combines multiple advisory forecasts without mutating operational truth."""

    strategy = "weighted_average_phase_7b"

    def combine(self, members: Iterable[EnsembleMemberForecast]) -> EnsembleForecastResult:
        member_tuple = tuple(members)
        if not member_tuple:
            raise ValueError("At least one ensemble member forecast is required")

        first = member_tuple[0].output
        self._validate_member_contracts(member_tuple, first)

        positive_total = sum(max(0.0, float(member.weight)) for member in member_tuple)
        if positive_total <= 0:
            raise ValueError("Ensemble member weights must contain at least one positive value")

        normalized_weights = {
            member.model_id: member.normalized_weight(positive_total)
            for member in sorted(member_tuple, key=lambda candidate: candidate.model_id)
        }
        blended_quantity = round(
            sum(member.output.forecast_quantity * normalized_weights[member.model_id] for member in member_tuple),
            6,
        )
        blended_cover = self._weighted_optional_average(
            (member.output.projected_days_of_cover, normalized_weights[member.model_id]) for member in member_tuple
        )
        blended_confidence = round(
            sum(member.output.confidence * normalized_weights[member.model_id] for member in member_tuple),
            6,
        )
        stockout_risk = self._highest_risk(member.output.stockout_risk for member in member_tuple)
        evidence_refs = tuple(
            dict.fromkeys(ref for member in member_tuple for ref in member.output.evidence_refs)
        )
        explanation = (
            f"Combined {len(member_tuple)} advisory forecast model(s) using weighted average ensemble strategy.",
            f"Blended forecast quantity is {blended_quantity:.6f} over {first.forecast_days} days.",
            "Ensemble remained advisory-only and read-only; it did not mutate inventory, movements, purchase orders, or ledger truth.",
        )
        output = ForecastModelOutput(
            item_id=first.item_id,
            location_id=first.location_id,
            environment=first.environment,
            forecast_days=first.forecast_days,
            forecast_quantity=blended_quantity,
            projected_days_of_cover=blended_cover,
            stockout_risk=stockout_risk,
            confidence=blended_confidence,
            explanation=explanation,
            evidence_refs=evidence_refs,
            advisory_only=True,
            inventory_source_of_truth_preserved=True,
            model_name="ensemble_weighted_average",
            model_version="7B.1",
        )
        audit_record = EnsembleForecastAuditRecord(
            strategy=self.strategy,
            member_count=len(member_tuple),
            member_weights=normalized_weights,
        )
        return EnsembleForecastResult(
            output=output,
            members=member_tuple,
            strategy=self.strategy,
            audit_record=audit_record,
            explanation=explanation,
        )

    def _validate_member_contracts(
        self,
        members: tuple[EnsembleMemberForecast, ...],
        first: ForecastModelOutput,
    ) -> None:
        for member in members:
            output = member.output
            if not output.advisory_only or not output.inventory_source_of_truth_preserved:
                raise ValueError("Ensemble members must preserve advisory-only and source-of-truth guardrails")
            if output.item_id != first.item_id or output.location_id != first.location_id:
                raise ValueError("Ensemble members must target the same item and location")
            if output.environment != first.environment:
                raise ValueError("Ensemble members must target the same environment")
            if output.forecast_days != first.forecast_days:
                raise ValueError("Ensemble members must use the same forecast horizon")

    def _weighted_optional_average(self, values: Iterable[tuple[float | None, float]]) -> float | None:
        available = tuple((value, weight) for value, weight in values if value is not None)
        total = sum(weight for _, weight in available)
        if total <= 0:
            return None
        return round(sum(float(value) * weight for value, weight in available) / total, 6)

    def _highest_risk(self, risks: Iterable[str]) -> str:
        risk_rank = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
        return max(risks, key=lambda risk: risk_rank.get(risk.upper(), 1))
