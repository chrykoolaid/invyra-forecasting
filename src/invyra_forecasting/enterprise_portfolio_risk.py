from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

from invyra_forecasting.enterprise_forecast_health import EnterpriseForecastHealth

ENTERPRISE_PORTFOLIO_RISK_SCHEMA_VERSION = "1.0.0"


class EnterprisePortfolioRiskType(str, Enum):
    NO_EVIDENCE = "no_evidence"
    LOW_COVERAGE = "low_coverage"
    INCOMPLETE_QUALITY_METRICS = "incomplete_quality_metrics"
    WEAK_ACCURACY = "weak_accuracy"
    CALIBRATION_CONCERN = "calibration_concern"


class EnterprisePortfolioRiskSeverity(str, Enum):
    INFORMATIONAL = "informational"
    WATCH = "watch"
    ELEVATED = "elevated"


@dataclass(frozen=True)
class EnterprisePortfolioRiskSignal:
    risk_type: EnterprisePortfolioRiskType
    severity: EnterprisePortfolioRiskSeverity
    reason: str
    observed_value: float | None
    threshold: float | None
    evidence_refs: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["risk_type"] = self.risk_type.value
        payload["severity"] = self.severity.value
        payload["evidence_refs"] = list(self.evidence_refs)
        return payload


@dataclass(frozen=True)
class EnterprisePortfolioRiskAssessment:
    namespace: str
    as_of_utc: str
    signal_count: int
    signals: tuple[EnterprisePortfolioRiskSignal, ...]
    schema_version: str = ENTERPRISE_PORTFOLIO_RISK_SCHEMA_VERSION
    advisory_only: bool = True
    read_only: bool = True
    inventory_source_of_truth_preserved: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "namespace": self.namespace,
            "as_of_utc": self.as_of_utc,
            "signal_count": self.signal_count,
            "signals": [signal.to_dict() for signal in self.signals],
            "schema_version": self.schema_version,
            "advisory_only": self.advisory_only,
            "read_only": self.read_only,
            "inventory_source_of_truth_preserved": self.inventory_source_of_truth_preserved,
        }


class EnterprisePortfolioRiskPolicy:
    """Emits explainable portfolio conditions without prediction or recommended action."""

    def assess(self, health: EnterpriseForecastHealth) -> EnterprisePortfolioRiskAssessment:
        signals: list[EnterprisePortfolioRiskSignal] = []
        refs = health.evidence_refs

        if health.total_eligible_evaluation_count == 0:
            signals.append(EnterprisePortfolioRiskSignal(
                EnterprisePortfolioRiskType.NO_EVIDENCE,
                EnterprisePortfolioRiskSeverity.INFORMATIONAL,
                "no certified portfolio evaluation evidence is available",
                0.0,
                None,
                refs,
            ))
        if health.model_version_count > 0 and health.evaluated_coverage_ratio < 0.5:
            signals.append(EnterprisePortfolioRiskSignal(
                EnterprisePortfolioRiskType.LOW_COVERAGE,
                EnterprisePortfolioRiskSeverity.ELEVATED,
                "fewer than half of registered model versions have certified evidence",
                health.evaluated_coverage_ratio,
                0.5,
                refs,
            ))
        if health.evaluated_model_version_count > 0 and (
            health.weighted_average_accuracy_score is None
            or health.weighted_average_calibration_gap is None
        ):
            signals.append(EnterprisePortfolioRiskSignal(
                EnterprisePortfolioRiskType.INCOMPLETE_QUALITY_METRICS,
                EnterprisePortfolioRiskSeverity.WATCH,
                "certified coverage exists but portfolio quality metrics are incomplete",
                None,
                None,
                refs,
            ))
        if health.weighted_average_accuracy_score is not None and health.weighted_average_accuracy_score < 0.8:
            signals.append(EnterprisePortfolioRiskSignal(
                EnterprisePortfolioRiskType.WEAK_ACCURACY,
                EnterprisePortfolioRiskSeverity.ELEVATED,
                "weighted certified accuracy is below the healthy threshold",
                health.weighted_average_accuracy_score,
                0.8,
                refs,
            ))
        if health.weighted_average_calibration_gap is not None and health.weighted_average_calibration_gap > 0.2:
            signals.append(EnterprisePortfolioRiskSignal(
                EnterprisePortfolioRiskType.CALIBRATION_CONCERN,
                EnterprisePortfolioRiskSeverity.ELEVATED,
                "weighted certified calibration gap exceeds the healthy threshold",
                health.weighted_average_calibration_gap,
                0.2,
                refs,
            ))

        return EnterprisePortfolioRiskAssessment(
            namespace=health.namespace,
            as_of_utc=health.as_of_utc,
            signal_count=len(signals),
            signals=tuple(signals),
        )
