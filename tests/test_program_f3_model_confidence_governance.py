from dataclasses import FrozenInstanceError

import pytest

from invyra_forecasting.model_confidence_governance import (
    ModelConfidenceGovernancePolicy,
    ModelConfidenceStatus,
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
        supported_forecast_horizons=(7, 14, 28),
        supported_demand_profiles=("seasonal",),
        namespace="default",
        registered_at_utc="2026-07-15T16:00:00+00:00",
    )


def _statistics(count: int, horizon: int | None = 7) -> ModelPerformanceStatistics:
    value = None if count == 0 else 0.8
    return ModelPerformanceStatistics(
        registry_id="registry-1",
        model_name="seasonal-naive",
        model_version="1.0",
        forecast_horizon_days=horizon,
        eligible_evaluation_count=count,
        mae=None if count == 0 else 2.0,
        rmse=None if count == 0 else 2.5,
        mape=None if count == 0 else 0.2,
        bias=None if count == 0 else 0.1,
        average_accuracy_score=value,
        average_calibration_gap=None if count == 0 else 0.05,
    )


@pytest.mark.parametrize(
    ("count", "expected"),
    [
        (0, ModelConfidenceStatus.EXPERIMENTAL),
        (1, ModelConfidenceStatus.LIMITED_EVIDENCE),
        (9, ModelConfidenceStatus.LIMITED_EVIDENCE),
        (10, ModelConfidenceStatus.DEVELOPING),
        (29, ModelConfidenceStatus.DEVELOPING),
        (30, ModelConfidenceStatus.TRUSTED),
        (99, ModelConfidenceStatus.TRUSTED),
        (100, ModelConfidenceStatus.ENTERPRISE_CERTIFIED),
    ],
)
def test_classifies_certified_evidence_volume(count, expected) -> None:
    assessment = ModelConfidenceGovernancePolicy().assess(_registry(), _statistics(count))

    assert assessment.confidence_status is expected
    assert assessment.eligible_evaluation_count == count
    assert assessment.qualification_reasons
    assert assessment.advisory_only is True
    assert assessment.read_only is True


def test_assessment_is_immutable_and_serializable() -> None:
    assessment = ModelConfidenceGovernancePolicy().assess(_registry(), _statistics(30))

    with pytest.raises(FrozenInstanceError):
        assessment.eligible_evaluation_count = 31
    payload = assessment.to_dict()
    assert payload["confidence_status"] == "trusted"
    assert payload["qualification_reasons"] == ["30 to 99 certified evaluations"]


def test_rejects_registry_statistics_identity_mismatch() -> None:
    statistics = ModelPerformanceStatistics(
        **{**_statistics(10).to_dict(), "model_version": "2.0"}
    )

    with pytest.raises(ValueError, match="registered model identity"):
        ModelConfidenceGovernancePolicy().assess(_registry(), statistics)


def test_rejects_unsupported_horizon() -> None:
    with pytest.raises(ValueError, match="not supported"):
        ModelConfidenceGovernancePolicy().assess(_registry(), _statistics(10, horizon=90))


def test_f3_does_not_score_rank_select_or_mutate_lifecycle() -> None:
    policy = ModelConfidenceGovernancePolicy()
    assessment = policy.assess(_registry(), _statistics(100))
    payload = assessment.to_dict()

    forbidden = {"score", "ranking_score", "rank", "weight", "selected", "lifecycle_status"}
    assert forbidden.isdisjoint(payload)
    assert not hasattr(policy, "select")
    assert not hasattr(policy, "rank")
    assert not hasattr(policy, "update_lifecycle")
