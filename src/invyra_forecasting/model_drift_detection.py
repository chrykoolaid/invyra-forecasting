from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

from invyra_forecasting.model_performance_registry import ModelPerformanceRegistryEntry
from invyra_forecasting.model_performance_statistics import ModelPerformanceStatistics

MODEL_DRIFT_DETECTION_SCHEMA_VERSION = "1.0.0"


class ModelDriftStatus(str, Enum):
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    STABLE = "stable"
    WATCH = "watch"
    DRIFT_DETECTED = "drift_detected"


@dataclass(frozen=True)
class ModelDriftThresholds:
    accuracy_drop_watch: float = 0.05
    accuracy_drop_drift: float = 0.10
    absolute_bias_increase_watch: float = 0.05
    absolute_bias_increase_drift: float = 0.10
    calibration_gap_increase_watch: float = 0.05
    calibration_gap_increase_drift: float = 0.10
    minimum_evaluations_per_window: int = 10

    def __post_init__(self) -> None:
        if any(value < 0 for value in (
            self.accuracy_drop_watch,
            self.accuracy_drop_drift,
            self.absolute_bias_increase_watch,
            self.absolute_bias_increase_drift,
            self.calibration_gap_increase_watch,
            self.calibration_gap_increase_drift,
        )):
            raise ValueError("drift thresholds must not be negative")
        if self.accuracy_drop_drift < self.accuracy_drop_watch:
            raise ValueError("accuracy drift threshold must be at least the watch threshold")
        if self.absolute_bias_increase_drift < self.absolute_bias_increase_watch:
            raise ValueError("bias drift threshold must be at least the watch threshold")
        if self.calibration_gap_increase_drift < self.calibration_gap_increase_watch:
            raise ValueError("calibration drift threshold must be at least the watch threshold")
        if self.minimum_evaluations_per_window < 1:
            raise ValueError("minimum_evaluations_per_window must be positive")


@dataclass(frozen=True)
class ModelDriftAssessment:
    registry_id: str
    model_name: str
    model_version: str
    forecast_horizon_days: int | None
    status: ModelDriftStatus
    baseline_evaluation_count: int
    current_evaluation_count: int
    accuracy_change: float | None
    absolute_bias_change: float | None
    calibration_gap_change: float | None
    reasons: tuple[str, ...]
    schema_version: str = MODEL_DRIFT_DETECTION_SCHEMA_VERSION
    advisory_only: bool = True
    read_only: bool = True
    inventory_source_of_truth_preserved: bool = True

    def __post_init__(self) -> None:
        if not self.registry_id or not self.model_name or not self.model_version:
            raise ValueError("registry and model identity are required")
        if self.baseline_evaluation_count < 0 or self.current_evaluation_count < 0:
            raise ValueError("evaluation counts must not be negative")
        if not self.reasons:
            raise ValueError("at least one drift reason is required")
        if self.schema_version != MODEL_DRIFT_DETECTION_SCHEMA_VERSION:
            raise ValueError("unsupported model drift detection schema version")
        if not self.advisory_only or not self.read_only:
            raise ValueError("model drift assessments must remain advisory-only and read-only")
        if not self.inventory_source_of_truth_preserved:
            raise ValueError("inventory source of truth must be preserved")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["status"] = self.status.value
        payload["reasons"] = list(self.reasons)
        return payload


class ModelDriftDetectionPolicy:
    """Compares certified statistics windows without changing model behaviour."""

    def __init__(self, thresholds: ModelDriftThresholds | None = None) -> None:
        self._thresholds = thresholds or ModelDriftThresholds()

    def assess(
        self,
        registry_entry: ModelPerformanceRegistryEntry,
        baseline: ModelPerformanceStatistics,
        current: ModelPerformanceStatistics,
    ) -> ModelDriftAssessment:
        self._validate_identity(registry_entry, baseline, current)
        minimum = self._thresholds.minimum_evaluations_per_window
        metrics = (
            baseline.average_accuracy_score,
            current.average_accuracy_score,
            baseline.bias,
            current.bias,
            baseline.average_calibration_gap,
            current.average_calibration_gap,
        )
        if baseline.eligible_evaluation_count < minimum or current.eligible_evaluation_count < minimum or any(value is None for value in metrics):
            return self._build(registry_entry, baseline, current, ModelDriftStatus.INSUFFICIENT_EVIDENCE, None, None, None, ("both windows require complete certified statistics and sufficient evaluation depth",))

        accuracy_change = round(current.average_accuracy_score - baseline.average_accuracy_score, 4)
        absolute_bias_change = round(abs(current.bias) - abs(baseline.bias), 4)
        calibration_change = round(current.average_calibration_gap - baseline.average_calibration_gap, 4)
        watch: list[str] = []
        drift: list[str] = []
        self._classify(-accuracy_change, self._thresholds.accuracy_drop_watch, self._thresholds.accuracy_drop_drift, "accuracy decreased", watch, drift)
        self._classify(absolute_bias_change, self._thresholds.absolute_bias_increase_watch, self._thresholds.absolute_bias_increase_drift, "absolute bias increased", watch, drift)
        self._classify(calibration_change, self._thresholds.calibration_gap_increase_watch, self._thresholds.calibration_gap_increase_drift, "calibration gap increased", watch, drift)

        if drift:
            status, reasons = ModelDriftStatus.DRIFT_DETECTED, tuple(drift + watch)
        elif watch:
            status, reasons = ModelDriftStatus.WATCH, tuple(watch)
        else:
            status, reasons = ModelDriftStatus.STABLE, ("certified performance changes remained within configured drift thresholds",)
        return self._build(registry_entry, baseline, current, status, accuracy_change, absolute_bias_change, calibration_change, reasons)

    @staticmethod
    def _classify(value: float, watch_threshold: float, drift_threshold: float, label: str, watch: list[str], drift: list[str]) -> None:
        if value >= drift_threshold:
            drift.append(f"{label} beyond the drift threshold")
        elif value >= watch_threshold:
            watch.append(f"{label} beyond the watch threshold")

    @staticmethod
    def _validate_identity(registry_entry: ModelPerformanceRegistryEntry, baseline: ModelPerformanceStatistics, current: ModelPerformanceStatistics) -> None:
        expected = (registry_entry.registry_id, registry_entry.model_name, registry_entry.model_version)
        for statistics in (baseline, current):
            if (statistics.registry_id, statistics.model_name, statistics.model_version) != expected:
                raise ValueError("drift statistics must match the registered model identity")
            if statistics.forecast_horizon_days is not None and statistics.forecast_horizon_days not in registry_entry.supported_forecast_horizons:
                raise ValueError("drift statistics horizon is not supported by the registered model")
            if not statistics.advisory_only or not statistics.read_only:
                raise ValueError("drift statistics must remain advisory-only and read-only")
            if not statistics.inventory_source_of_truth_preserved:
                raise ValueError("inventory source of truth must be preserved")
        if baseline.forecast_horizon_days != current.forecast_horizon_days:
            raise ValueError("baseline and current statistics horizons must match")

    @staticmethod
    def _build(registry_entry: ModelPerformanceRegistryEntry, baseline: ModelPerformanceStatistics, current: ModelPerformanceStatistics, status: ModelDriftStatus, accuracy_change: float | None, absolute_bias_change: float | None, calibration_gap_change: float | None, reasons: tuple[str, ...]) -> ModelDriftAssessment:
        return ModelDriftAssessment(
            registry_id=registry_entry.registry_id,
            model_name=registry_entry.model_name,
            model_version=registry_entry.model_version,
            forecast_horizon_days=current.forecast_horizon_days,
            status=status,
            baseline_evaluation_count=baseline.eligible_evaluation_count,
            current_evaluation_count=current.eligible_evaluation_count,
            accuracy_change=accuracy_change,
            absolute_bias_change=absolute_bias_change,
            calibration_gap_change=calibration_gap_change,
            reasons=reasons,
        )
