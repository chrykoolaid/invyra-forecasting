from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any

from invyra_forecasting.evaluation.persistence import ForecastEvaluationRecord


class DriftSeverity(StrEnum):
    NONE = "NONE"
    WATCH = "WATCH"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class DriftDetectionPolicy:
    minimum_records: int = 4
    recent_window_size: int = 2
    accuracy_drop_watch: float = 0.05
    accuracy_drop_warning: float = 0.12
    accuracy_drop_critical: float = 0.25
    calibration_gap_warning: float = 0.20
    bias_warning: float = 0.0

    def __post_init__(self) -> None:
        if self.minimum_records < 2:
            raise ValueError("minimum_records must be at least 2")
        if self.recent_window_size < 1:
            raise ValueError("recent_window_size must be at least 1")
        if self.recent_window_size >= self.minimum_records:
            raise ValueError("recent_window_size must be smaller than minimum_records")


@dataclass(frozen=True)
class DriftIndicator:
    name: str
    value: float | None
    threshold: float | None
    severity: DriftSeverity
    explanation: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["severity"] = self.severity.value
        return payload


@dataclass(frozen=True)
class DriftReport:
    model_name: str
    model_version: str
    record_count: int
    severity: DriftSeverity
    indicators: tuple[DriftIndicator, ...]
    recommendation: str
    advisory_only: bool = True
    read_only: bool = True
    inventory_source_of_truth_preserved: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.advisory_only:
            raise ValueError("drift reports must remain advisory-only")
        if not self.read_only:
            raise ValueError("drift reports must remain read-only")
        if not self.inventory_source_of_truth_preserved:
            raise ValueError("inventory source of truth must be preserved")

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_name": self.model_name,
            "model_version": self.model_version,
            "record_count": self.record_count,
            "severity": self.severity.value,
            "indicators": [indicator.to_dict() for indicator in self.indicators],
            "recommendation": self.recommendation,
            "advisory_only": self.advisory_only,
            "read_only": self.read_only,
            "inventory_source_of_truth_preserved": self.inventory_source_of_truth_preserved,
            "metadata": dict(self.metadata),
        }


class DriftDetectionService:
    def __init__(self, policy: DriftDetectionPolicy | None = None) -> None:
        self._policy = policy or DriftDetectionPolicy()

    def detect(self, records: tuple[ForecastEvaluationRecord, ...]) -> DriftReport:
        ordered = tuple(sorted(records, key=lambda record: (record.persisted_at_utc, record.evaluation_id)))
        model_name, model_version = self._model_identity(ordered)
        if len(ordered) < self._policy.minimum_records:
            indicator = DriftIndicator(
                name="insufficient_history",
                value=float(len(ordered)),
                threshold=float(self._policy.minimum_records),
                severity=DriftSeverity.WATCH,
                explanation="Not enough persisted evaluation records exist to determine model drift reliably.",
            )
            return DriftReport(
                model_name=model_name,
                model_version=model_version,
                record_count=len(ordered),
                severity=DriftSeverity.WATCH,
                indicators=(indicator,),
                recommendation="Continue collecting evaluation evidence before changing model governance.",
            )

        recent = ordered[-self._policy.recent_window_size :]
        baseline = ordered[: -self._policy.recent_window_size]
        baseline_accuracy = self._average(record.result.accuracy_score for record in baseline)
        recent_accuracy = self._average(record.result.accuracy_score for record in recent)
        accuracy_drop = round(baseline_accuracy - recent_accuracy, 6)
        recent_calibration_gap = self._average(record.result.calibration_gap for record in recent)
        recent_bias = self._average(record.result.bias for record in recent)

        indicators = (
            self._accuracy_drop_indicator(accuracy_drop),
            self._calibration_indicator(recent_calibration_gap),
            self._bias_indicator(recent_bias),
        )
        severity = self._highest_severity(indicators)
        return DriftReport(
            model_name=model_name,
            model_version=model_version,
            record_count=len(ordered),
            severity=severity,
            indicators=indicators,
            recommendation=self._recommendation(severity),
            metadata={
                "baseline_accuracy": round(baseline_accuracy, 6),
                "recent_accuracy": round(recent_accuracy, 6),
                "recent_window_size": self._policy.recent_window_size,
            },
        )

    def _model_identity(self, records: tuple[ForecastEvaluationRecord, ...]) -> tuple[str, str]:
        if not records:
            return "UNKNOWN", "UNKNOWN"
        first = records[0]
        return first.model_name, first.model_version

    def _accuracy_drop_indicator(self, accuracy_drop: float) -> DriftIndicator:
        if accuracy_drop >= self._policy.accuracy_drop_critical:
            severity = DriftSeverity.CRITICAL
            threshold = self._policy.accuracy_drop_critical
        elif accuracy_drop >= self._policy.accuracy_drop_warning:
            severity = DriftSeverity.WARNING
            threshold = self._policy.accuracy_drop_warning
        elif accuracy_drop >= self._policy.accuracy_drop_watch:
            severity = DriftSeverity.WATCH
            threshold = self._policy.accuracy_drop_watch
        else:
            severity = DriftSeverity.NONE
            threshold = self._policy.accuracy_drop_watch
        return DriftIndicator(
            name="accuracy_drop",
            value=accuracy_drop,
            threshold=threshold,
            severity=severity,
            explanation=f"Recent accuracy changed by {-accuracy_drop:.6f} compared with the historical baseline.",
        )

    def _calibration_indicator(self, calibration_gap: float) -> DriftIndicator:
        severity = DriftSeverity.WARNING if calibration_gap >= self._policy.calibration_gap_warning else DriftSeverity.NONE
        return DriftIndicator(
            name="calibration_gap",
            value=round(calibration_gap, 6),
            threshold=self._policy.calibration_gap_warning,
            severity=severity,
            explanation="Recent confidence calibration gap compared confidence with measured accuracy.",
        )

    def _bias_indicator(self, bias: float) -> DriftIndicator:
        if self._policy.bias_warning <= 0:
            severity = DriftSeverity.NONE
        else:
            severity = DriftSeverity.WARNING if abs(bias) >= self._policy.bias_warning else DriftSeverity.NONE
        return DriftIndicator(
            name="bias",
            value=round(bias, 6),
            threshold=self._policy.bias_warning,
            severity=severity,
            explanation="Recent forecast bias indicates whether forecasts are consistently under or over actual outcomes.",
        )

    def _highest_severity(self, indicators: tuple[DriftIndicator, ...]) -> DriftSeverity:
        order = {
            DriftSeverity.NONE: 0,
            DriftSeverity.WATCH: 1,
            DriftSeverity.WARNING: 2,
            DriftSeverity.CRITICAL: 3,
        }
        return max((indicator.severity for indicator in indicators), key=lambda severity: order[severity])

    def _recommendation(self, severity: DriftSeverity) -> str:
        if severity == DriftSeverity.CRITICAL:
            return "Review model lifecycle status and consider retiring or replacing the model after human approval."
        if severity == DriftSeverity.WARNING:
            return "Investigate model performance and monitor upcoming evaluations before promotion decisions."
        if severity == DriftSeverity.WATCH:
            return "Continue monitoring because early drift indicators are present."
        return "No drift action is recommended. Continue normal evaluation monitoring."

    def _average(self, values) -> float:
        numbers = list(values)
        if not numbers:
            return 0.0
        return sum(numbers) / len(numbers)
