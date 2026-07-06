from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from invyra_forecasting.models.contracts import ForecastModelOutput


@dataclass(frozen=True)
class ForecastDecisionGateConfiguration:
    """Versioned thresholds for advisory forecast decision readiness."""

    version: str = "8A.1"
    minimum_confidence: float = 0.55
    minimum_evidence_refs: int = 1
    critical_risk_requires_high_confidence: float = 0.70

    def to_dict(self) -> dict[str, object]:
        return {
            "version": self.version,
            "minimum_confidence": self.minimum_confidence,
            "minimum_evidence_refs": self.minimum_evidence_refs,
            "critical_risk_requires_high_confidence": self.critical_risk_requires_high_confidence,
        }


@dataclass(frozen=True)
class ForecastDecisionGateResult:
    """Read-only advisory assessment of whether a forecast is decision-ready."""

    decision_ready: bool
    reasons: tuple[str, ...]
    warnings: tuple[str, ...]
    configuration: ForecastDecisionGateConfiguration = field(default_factory=ForecastDecisionGateConfiguration)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, object]:
        return {
            "decision_ready": self.decision_ready,
            "reasons": list(self.reasons),
            "warnings": list(self.warnings),
            "configuration": self.configuration.to_dict(),
            "created_at": self.created_at,
            "advisory_only": True,
            "read_only": True,
            "inventory_source_of_truth_preserved": True,
        }


class ForecastDecisionGateEvaluator:
    """Evaluates forecast outputs without mutating inventory or recommendations."""

    def __init__(self, configuration: ForecastDecisionGateConfiguration | None = None) -> None:
        self._configuration = configuration or ForecastDecisionGateConfiguration()

    @property
    def configuration(self) -> ForecastDecisionGateConfiguration:
        return self._configuration

    def evaluate(self, output: ForecastModelOutput) -> ForecastDecisionGateResult:
        warnings: list[str] = []
        reasons: list[str] = []

        if not output.advisory_only:
            warnings.append("Forecast output is not marked advisory-only.")
        else:
            reasons.append("Forecast output is advisory-only.")

        if not output.inventory_source_of_truth_preserved:
            warnings.append("Forecast output does not preserve Inventory as source of truth.")
        else:
            reasons.append("Inventory source-of-truth guardrail is preserved.")

        if output.confidence < self._configuration.minimum_confidence:
            warnings.append(
                f"Forecast confidence {output.confidence:.6f} is below minimum {self._configuration.minimum_confidence:.6f}."
            )
        else:
            reasons.append("Forecast confidence meets the decision-readiness threshold.")

        evidence_count = len(output.evidence_refs)
        if evidence_count < self._configuration.minimum_evidence_refs:
            warnings.append(
                f"Forecast has {evidence_count} evidence reference(s); minimum required is {self._configuration.minimum_evidence_refs}."
            )
        else:
            reasons.append("Forecast has sufficient evidence references for advisory review.")

        if output.stockout_risk.upper() == "CRITICAL" and output.confidence < self._configuration.critical_risk_requires_high_confidence:
            warnings.append(
                "Critical stockout risk requires higher confidence before being marked decision-ready."
            )
        elif output.stockout_risk.upper() == "CRITICAL":
            reasons.append("Critical stockout risk is backed by sufficient confidence.")

        reasons.append(
            "Decision gate remained advisory-only and read-only; it did not mutate inventory, movements, purchase orders, or ledger truth."
        )

        return ForecastDecisionGateResult(
            decision_ready=not warnings,
            reasons=tuple(reasons),
            warnings=tuple(warnings),
            configuration=self._configuration,
        )
