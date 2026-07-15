from dataclasses import FrozenInstanceError

import pytest

from invyra_forecasting.model_drift_detection import (
    ModelDriftDetectionPolicy,
    ModelDriftStatus,
    ModelDriftThresholds,
)
from invyra_forecasting.model_performance_registry import (
    ModelLifecycleStatus,
    ModelPerformanceRegistryEntry,
)
from invyra_forecasting.model_performance_statistics import ModelPerformanceStatistics


def _registry() -> ModelPerformanceRegistryEntry:
    return ModelPerformanceRegistryEntry(
        registry_id="registry-1",
        model_name="seasonal-naive",
        model_version="1.0",
        lifecycle_status=ModelLifecycleStatus.ACTIVE,
        supported_forecast_horizons=(7, 14),
        supported_demand_profiles=("seasonal",),
        namespace="default",
        registered_at_utc="2026-07-15T16:00:00+00:00",
    )


def _stats(*, count=30, accuracy=0.9, bias=0.02, calibration=0.04, horizon=7):
    return ModelPerformanceStatistics(
        registry_id="registry-1",
        model_name="seasonal-naive",
        model_version="1.0",
        forecast_horizon_days=horizon,
        eligible_evaluation_count=count,
        mae=2.0,
        rmse=2.5,
        mape=0.2,
        bias=bias,
        average_accuracy_score=accuracy,
        average_calibration_gap=calibration,
    )


def test_classifies_stable_certified_performance() -> None:
    result = ModelDriftDetectionPolicy().assess(
        _registry(),
        _stats(),
        _stats(accuracy=0.88, bias=0.04, calibration=0.06),
    )

    assert result.status is ModelDriftStatus.STABLE
    assert result.accuracy_change == -0.02
    assert result.absolute_bias_change == 0.02
    assert result.calibration_gap_change == 0.02


def test_classifies_watch_and_drift_thresholds() -> None:
    policy = ModelDriftDetectionPolicy()

    watch = policy.assess(
        _registry(),
        _stats(),
        _stats(accuracy=0.84, bias=0.08, calibration=0.10),
    )
    drift = policy.assess(
        _registry(),
        _stats(),
        _stats(accuracy=0.78, bias=0.15, calibration=0.16),
    )

    assert watch.status is ModelDriftStatus.WATCH
    assert drift.status is ModelDriftStatus.DRIFT_DETECTED
    assert any("accuracy decreased" in reason for reason in drift.reasons)


def test_requires_sufficient_complete_certified_windows() -> None:
    result = ModelDriftDetectionPolicy().assess(
        _registry(),
        _stats(count=9),
        _stats(count=30),
    )

    assert result.status is ModelDriftStatus.INSUFFICIENT_EVIDENCE
    assert result.accuracy_change is None


def test_validates_identity_and_matching_horizon() -> None:
    mismatched = ModelPerformanceStatistics(
        **{**_stats().to_dict(), "model_version": "2.0"}
    )
    with pytest.raises(ValueError, match="registered model identity"):
        ModelDriftDetectionPolicy().assess(_registry(), _stats(), mismatched)

    with pytest.raises(ValueError, match="horizons must match"):
        ModelDriftDetectionPolicy().assess(_registry(), _stats(horizon=7), _stats(horizon=14))


def test_assessment_is_immutable_serializable_and_advisory_only() -> None:
    policy = ModelDriftDetectionPolicy()
    result = policy.assess(_registry(), _stats(), _stats())

    with pytest.raises(FrozenInstanceError):
        result.status = ModelDriftStatus.DRIFT_DETECTED
    payload = result.to_dict()
    assert payload["status"] == "stable"
    assert payload["advisory_only"] is True
    assert payload["read_only"] is True
    assert not hasattr(policy, "retrain")
    assert not hasattr(policy, "retire")
    assert not hasattr(policy, "select")


def test_validates_threshold_configuration() -> None:
    with pytest.raises(ValueError, match="at least the watch threshold"):
        ModelDriftThresholds(accuracy_drop_watch=0.2, accuracy_drop_drift=0.1)
