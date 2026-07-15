from dataclasses import FrozenInstanceError

import pytest

from invyra_forecasting.model_confidence_governance import (
    ModelConfidenceAssessment,
    ModelConfidenceStatus,
)
from invyra_forecasting.model_drift_detection import (
    ModelDriftAssessment,
    ModelDriftStatus,
)
from invyra_forecasting.model_performance_registry import (
    ModelLifecycleStatus,
    ModelPerformanceRegistryEntry,
)
from invyra_forecasting.model_retirement_governance import (
    ModelLifecycleRecommendation,
    ModelRetirementGovernancePolicy,
)


def _registry(status: ModelLifecycleStatus = ModelLifecycleStatus.ACTIVE):
    return ModelPerformanceRegistryEntry(
        registry_id="registry-1",
        model_name="seasonal-naive",
        model_version="1.0",
        lifecycle_status=status,
        supported_forecast_horizons=(7, 14),
        supported_demand_profiles=("seasonal",),
        namespace="default",
        registered_at_utc="2026-07-15T16:00:00+00:00",
    )


def _confidence():
    return ModelConfidenceAssessment(
        registry_id="registry-1",
        model_name="seasonal-naive",
        model_version="1.0",
        forecast_horizon_days=7,
        confidence_status=ModelConfidenceStatus.TRUSTED,
        eligible_evaluation_count=40,
        qualification_reasons=("30 to 99 certified evaluations",),
    )


def _drift(status: ModelDriftStatus):
    return ModelDriftAssessment(
        registry_id="registry-1",
        model_name="seasonal-naive",
        model_version="1.0",
        forecast_horizon_days=7,
        status=status,
        baseline_evaluation_count=30,
        current_evaluation_count=30,
        accuracy_change=-0.12 if status is ModelDriftStatus.DRIFT_DETECTED else -0.02,
        absolute_bias_change=0.11 if status is ModelDriftStatus.DRIFT_DETECTED else 0.02,
        calibration_gap_change=0.11 if status is ModelDriftStatus.DRIFT_DETECTED else 0.02,
        reasons=("certified drift evidence",),
    )


@pytest.mark.parametrize(
    ("current", "expected_recommendation", "expected_target"),
    [
        (ModelLifecycleStatus.ACTIVE, ModelLifecycleRecommendation.MOVE_TO_OBSERVATION, ModelLifecycleStatus.OBSERVATION),
        (ModelLifecycleStatus.OBSERVATION, ModelLifecycleRecommendation.DEPRECATE, ModelLifecycleStatus.DEPRECATED),
        (ModelLifecycleStatus.DEPRECATED, ModelLifecycleRecommendation.RETIRE, ModelLifecycleStatus.RETIRED),
        (ModelLifecycleStatus.RETIRED, ModelLifecycleRecommendation.RETAIN_RETIRED, ModelLifecycleStatus.RETIRED),
    ],
)
def test_escalates_one_governed_step_without_mutating_registry(current, expected_recommendation, expected_target):
    registry = _registry(current)
    decision = ModelRetirementGovernancePolicy().assess(
        registry,
        _confidence(),
        _drift(ModelDriftStatus.DRIFT_DETECTED),
    )

    assert decision.recommendation is expected_recommendation
    assert decision.recommended_lifecycle_status is expected_target
    assert registry.lifecycle_status is current
    assert decision.explicit_approval_required is True
    assert decision.automatic_transition_permitted is False


def test_watch_moves_active_model_to_observation_recommendation_only():
    decision = ModelRetirementGovernancePolicy().assess(
        _registry(),
        _confidence(),
        _drift(ModelDriftStatus.WATCH),
    )

    assert decision.recommendation is ModelLifecycleRecommendation.MOVE_TO_OBSERVATION
    assert decision.recommended_lifecycle_status is ModelLifecycleStatus.OBSERVATION


def test_stable_or_insufficient_evidence_does_not_escalate():
    policy = ModelRetirementGovernancePolicy()
    stable = policy.assess(_registry(), _confidence(), _drift(ModelDriftStatus.STABLE))
    insufficient = policy.assess(
        _registry(), _confidence(), _drift(ModelDriftStatus.INSUFFICIENT_EVIDENCE)
    )

    assert stable.recommendation is ModelLifecycleRecommendation.MAINTAIN
    assert insufficient.recommendation is ModelLifecycleRecommendation.MAINTAIN
    assert stable.recommended_lifecycle_status is ModelLifecycleStatus.ACTIVE


def test_validates_cross_contract_identity_and_horizon():
    mismatched_confidence = ModelConfidenceAssessment(
        **{**_confidence().to_dict(), "model_version": "2.0", "confidence_status": ModelConfidenceStatus.TRUSTED}
    )
    with pytest.raises(ValueError, match="registered model identity"):
        ModelRetirementGovernancePolicy().assess(
            _registry(), mismatched_confidence, _drift(ModelDriftStatus.STABLE)
        )

    mismatched_drift = ModelDriftAssessment(
        **{**_drift(ModelDriftStatus.STABLE).to_dict(), "forecast_horizon_days": 14, "status": ModelDriftStatus.STABLE}
    )
    with pytest.raises(ValueError, match="horizons must match"):
        ModelRetirementGovernancePolicy().assess(
            _registry(), _confidence(), mismatched_drift
        )


def test_decision_is_immutable_serializable_and_has_no_mutation_surface():
    policy = ModelRetirementGovernancePolicy()
    decision = policy.assess(
        _registry(ModelLifecycleStatus.DEPRECATED),
        _confidence(),
        _drift(ModelDriftStatus.DRIFT_DETECTED),
    )

    with pytest.raises(FrozenInstanceError):
        decision.recommendation = ModelLifecycleRecommendation.MAINTAIN
    payload = decision.to_dict()
    assert payload["recommendation"] == "retire"
    assert payload["current_lifecycle_status"] == "deprecated"
    assert payload["recommended_lifecycle_status"] == "retired"
    assert not hasattr(policy, "apply")
    assert not hasattr(policy, "retire")
    assert not hasattr(policy, "disable")
    assert not hasattr(policy, "select")
