from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

from invyra_forecasting.model_confidence_governance import ModelConfidenceAssessment
from invyra_forecasting.model_drift_detection import ModelDriftAssessment, ModelDriftStatus
from invyra_forecasting.model_performance_registry import (
    ModelLifecycleStatus,
    ModelPerformanceRegistryEntry,
)

MODEL_RETIREMENT_GOVERNANCE_SCHEMA_VERSION = "1.0.0"


class ModelLifecycleRecommendation(str, Enum):
    MAINTAIN = "maintain"
    MOVE_TO_OBSERVATION = "move_to_observation"
    DEPRECATE = "deprecate"
    RETIRE = "retire"
    RETAIN_RETIRED = "retain_retired"


@dataclass(frozen=True)
class ModelRetirementGovernanceDecision:
    registry_id: str
    model_name: str
    model_version: str
    current_lifecycle_status: ModelLifecycleStatus
    recommended_lifecycle_status: ModelLifecycleStatus
    recommendation: ModelLifecycleRecommendation
    confidence_status: str
    drift_status: ModelDriftStatus
    reasons: tuple[str, ...]
    explicit_approval_required: bool = True
    automatic_transition_permitted: bool = False
    schema_version: str = MODEL_RETIREMENT_GOVERNANCE_SCHEMA_VERSION
    advisory_only: bool = True
    read_only: bool = True
    inventory_source_of_truth_preserved: bool = True

    def __post_init__(self) -> None:
        if not self.registry_id or not self.model_name or not self.model_version:
            raise ValueError("registry and model identity are required")
        if not self.reasons:
            raise ValueError("at least one governance reason is required")
        if not self.explicit_approval_required:
            raise ValueError("model lifecycle transitions require explicit approval")
        if self.automatic_transition_permitted:
            raise ValueError("automatic lifecycle transitions are not permitted")
        if self.schema_version != MODEL_RETIREMENT_GOVERNANCE_SCHEMA_VERSION:
            raise ValueError("unsupported model retirement governance schema version")
        if not self.advisory_only or not self.read_only:
            raise ValueError("retirement governance decisions must remain advisory-only and read-only")
        if not self.inventory_source_of_truth_preserved:
            raise ValueError("inventory source of truth must be preserved")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["current_lifecycle_status"] = self.current_lifecycle_status.value
        payload["recommended_lifecycle_status"] = self.recommended_lifecycle_status.value
        payload["recommendation"] = self.recommendation.value
        payload["drift_status"] = self.drift_status.value
        payload["reasons"] = list(self.reasons)
        return payload


class ModelRetirementGovernancePolicy:
    """Produces non-binding lifecycle recommendations without mutating model state."""

    def assess(
        self,
        registry_entry: ModelPerformanceRegistryEntry,
        confidence: ModelConfidenceAssessment,
        drift: ModelDriftAssessment,
    ) -> ModelRetirementGovernanceDecision:
        self._validate_identity(registry_entry, confidence, drift)
        current = registry_entry.lifecycle_status

        if current is ModelLifecycleStatus.RETIRED:
            recommendation = ModelLifecycleRecommendation.RETAIN_RETIRED
            target = ModelLifecycleStatus.RETIRED
            reasons = ("model is already retired and remains excluded pending separate approved reactivation governance",)
        elif drift.status is ModelDriftStatus.DRIFT_DETECTED:
            recommendation, target, reasons = self._escalate(current)
        elif drift.status is ModelDriftStatus.WATCH:
            if current is ModelLifecycleStatus.ACTIVE:
                recommendation = ModelLifecycleRecommendation.MOVE_TO_OBSERVATION
                target = ModelLifecycleStatus.OBSERVATION
                reasons = ("drift watch signal warrants governed observation before stronger lifecycle action",)
            else:
                recommendation = ModelLifecycleRecommendation.MAINTAIN
                target = current
                reasons = ("drift watch signal does not justify another lifecycle escalation",)
        elif drift.status is ModelDriftStatus.INSUFFICIENT_EVIDENCE:
            recommendation = ModelLifecycleRecommendation.MAINTAIN
            target = current
            reasons = ("insufficient certified evidence prevents lifecycle escalation",)
        else:
            recommendation = ModelLifecycleRecommendation.MAINTAIN
            target = current
            reasons = ("certified performance is stable within configured drift thresholds",)

        return ModelRetirementGovernanceDecision(
            registry_id=registry_entry.registry_id,
            model_name=registry_entry.model_name,
            model_version=registry_entry.model_version,
            current_lifecycle_status=current,
            recommended_lifecycle_status=target,
            recommendation=recommendation,
            confidence_status=confidence.confidence_status.value,
            drift_status=drift.status,
            reasons=reasons,
        )

    @staticmethod
    def _escalate(
        current: ModelLifecycleStatus,
    ) -> tuple[ModelLifecycleRecommendation, ModelLifecycleStatus, tuple[str, ...]]:
        if current in (ModelLifecycleStatus.EXPERIMENTAL, ModelLifecycleStatus.ACTIVE):
            return (
                ModelLifecycleRecommendation.MOVE_TO_OBSERVATION,
                ModelLifecycleStatus.OBSERVATION,
                ("certified drift evidence warrants observation before deprecation",),
            )
        if current is ModelLifecycleStatus.OBSERVATION:
            return (
                ModelLifecycleRecommendation.DEPRECATE,
                ModelLifecycleStatus.DEPRECATED,
                ("continued certified drift while under observation warrants deprecation review",),
            )
        if current is ModelLifecycleStatus.DEPRECATED:
            return (
                ModelLifecycleRecommendation.RETIRE,
                ModelLifecycleStatus.RETIRED,
                ("continued certified drift after deprecation warrants retirement review",),
            )
        return (
            ModelLifecycleRecommendation.MAINTAIN,
            current,
            ("no stronger lifecycle action is justified",),
        )

    @staticmethod
    def _validate_identity(
        registry_entry: ModelPerformanceRegistryEntry,
        confidence: ModelConfidenceAssessment,
        drift: ModelDriftAssessment,
    ) -> None:
        expected = (
            registry_entry.registry_id,
            registry_entry.model_name,
            registry_entry.model_version,
        )
        if (confidence.registry_id, confidence.model_name, confidence.model_version) != expected:
            raise ValueError("confidence assessment must match the registered model identity")
        if (drift.registry_id, drift.model_name, drift.model_version) != expected:
            raise ValueError("drift assessment must match the registered model identity")
        if confidence.forecast_horizon_days != drift.forecast_horizon_days:
            raise ValueError("confidence and drift horizons must match")
        for item in (registry_entry, confidence, drift):
            if not item.advisory_only or not item.read_only:
                raise ValueError("retirement governance inputs must remain advisory-only and read-only")
            if not item.inventory_source_of_truth_preserved:
                raise ValueError("inventory source of truth must be preserved")
