from __future__ import annotations

from dataclasses import dataclass, field
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
class EnsembleConsensusConfiguration:
    """Configurable thresholds for advisory ensemble consensus checks."""

    version: str = "7C.1"
    minimum_member_count: int = 2
    minimum_confidence: float = 0.55
    maximum_quantity_spread_ratio: float = 0.35

    def to_dict(self) -> dict[str, object]:
        return {
            "version": self.version,
            "minimum_member_count": self.minimum_member_count,
            "minimum_confidence": self.minimum_confidence,
            "maximum_quantity_spread_ratio": self.maximum_quantity_spread_ratio,
        }


@dataclass(frozen=True)
class EnsembleConsensusAssessment:
    """Read-only assessment of ensemble agreement and operational suitability."""

    consensus_passed: bool
    member_count: int
    average_confidence: float
    quantity_spread_ratio: float
    warnings: tuple[str, ...]
    configuration: EnsembleConsensusConfiguration = field(default_factory=EnsembleConsensusConfiguration)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, object]:
        return {
            "consensus_passed": self.consensus_passed,
            "member_count": self.member_count,
            "average_confidence": self.average_confidence,
            "quantity_spread_ratio": self.quantity_spread_ratio,
            "warnings": list(self.warnings),
            "configuration": self.configuration.to_dict(),
            "created_at": self.created_at,
            "advisory_only": True,
            "read_only": True,
            "inventory_source_of_truth_preserved": True,
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
    consensus_assessment: EnsembleConsensusAssessment | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "output": self.output.to_dict(),
            "members": [member.to_dict() for member in self.members],
            "strategy": self.strategy,
            "audit_record": self.audit_record.to_dict(),
            "explanation": list(self.explanation),
            "consensus_assessment": self.consensus_assessment.to_dict() if self.consensus_assessment else None,
        }


class EnsembleConsensusPolicy:
    """Assesses ensemble quality without mutating forecasts or operational data."""

    def __init__(self, configuration: EnsembleConsensusConfiguration | None = None) -> None:
        self._configuration = configuration or EnsembleConsensusConfiguration()

    @property
    def configuration(self) -> EnsembleConsensusConfiguration:
        return self._configuration

    def assess(self, result: EnsembleForecastResult) -> EnsembleConsensusAssessment:
        quantities = tuple(member.output.forecast_quantity for member in result.members)
        confidences = tuple(member.output.confidence for member in result.members)
        member_count = len(result.members)
        average_confidence = round(sum(confidences) / member_count, 6) if member_count else 0.0
        quantity_spread_ratio = self._quantity_spread_ratio(quantities)
        warnings: list[str] = []

        if member_count < self._configuration.minimum_member_count:
            warnings.append(
                f"Ensemble has {member_count} member(s); minimum required is {self._configuration.minimum_member_count}."
            )
        if average_confidence < self._configuration.minimum_confidence:
            warnings.append(
                f"Average ensemble confidence {average_confidence:.6f} is below minimum {self._configuration.minimum_confidence:.6f}."
            )
        if quantity_spread_ratio > self._configuration.maximum_quantity_spread_ratio:
            warnings.append(
                f"Forecast quantity spread ratio {quantity_spread_ratio:.6f} exceeds maximum {self._configuration.maximum_quantity_spread_ratio:.6f}."
            )

        return EnsembleConsensusAssessment(
            consensus_passed=not warnings,
            member_count=member_count,
            average_confidence=average_confidence,
            quantity_spread_ratio=quantity_spread_ratio,
            warnings=tuple(warnings),
            configuration=self._configuration,
        )

    def _quantity_spread_ratio(self, quantities: tuple[float, ...]) -> float:
        if not quantities:
            return 0.0
        maximum = max(quantities)
        minimum = min(quantities)
        denominator = max(abs(sum(quantities) / len(quantities)), 1.0)
        return round((maximum - minimum) / denominator, 6)


class WeightedAverageEnsembleForecaster:
    """Combines multiple advisory forecasts without mutating operational truth."""

    strategy = "weighted_average_phase_7b"

    def __init__(self, consensus_policy: EnsembleConsensusPolicy | None = None) -> None:
        self._consensus_policy = consensus_policy

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
        result = EnsembleForecastResult(
            output=output,
            members=member_tuple,
            strategy=self.strategy,
            audit_record=audit_record,
            explanation=explanation,
        )
        if self._consensus_policy is None:
            return result
        return EnsembleForecastResult(
            output=result.output,
            members=result.members,
            strategy=result.strategy,
            audit_record=result.audit_record,
            explanation=result.explanation,
            consensus_assessment=self._consensus_policy.assess(result),
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
