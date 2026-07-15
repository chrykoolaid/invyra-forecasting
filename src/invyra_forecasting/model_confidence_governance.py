from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

from invyra_forecasting.model_performance_registry import ModelPerformanceRegistryEntry
from invyra_forecasting.model_performance_statistics import ModelPerformanceStatistics

MODEL_CONFIDENCE_GOVERNANCE_SCHEMA_VERSION = "1.0.0"


class ModelConfidenceStatus(str, Enum):
    EXPERIMENTAL = "experimental"
    LIMITED_EVIDENCE = "limited_evidence"
    DEVELOPING = "developing"
    TRUSTED = "trusted"
    ENTERPRISE_CERTIFIED = "enterprise_certified"


@dataclass(frozen=True)
class ModelConfidenceAssessment:
    registry_id: str
    model_name: str
    model_version: str
    forecast_horizon_days: int | None
    confidence_status: ModelConfidenceStatus
    eligible_evaluation_count: int
    qualification_reasons: tuple[str, ...]
    schema_version: str = MODEL_CONFIDENCE_GOVERNANCE_SCHEMA_VERSION
    advisory_only: bool = True
    read_only: bool = True
    inventory_source_of_truth_preserved: bool = True

    def __post_init__(self) -> None:
        if not self.registry_id or not self.model_name or not self.model_version:
            raise ValueError("registry and model identity are required")
        if self.eligible_evaluation_count < 0:
            raise ValueError("eligible_evaluation_count must not be negative")
        if not self.qualification_reasons:
            raise ValueError("at least one qualification reason is required")
        if self.schema_version != MODEL_CONFIDENCE_GOVERNANCE_SCHEMA_VERSION:
            raise ValueError("unsupported model confidence governance schema version")
        if not self.advisory_only or not self.read_only:
            raise ValueError("model confidence assessments must remain advisory-only and read-only")
        if not self.inventory_source_of_truth_preserved:
            raise ValueError("inventory source of truth must be preserved")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["confidence_status"] = self.confidence_status.value
        payload["qualification_reasons"] = list(self.qualification_reasons)
        return payload


class ModelConfidenceGovernancePolicy:
    """Classifies evidence maturity without scoring or selecting models."""

    def assess(
        self,
        registry_entry: ModelPerformanceRegistryEntry,
        statistics: ModelPerformanceStatistics,
    ) -> ModelConfidenceAssessment:
        self._validate_identity(registry_entry, statistics)
        count = statistics.eligible_evaluation_count

        if count == 0:
            status = ModelConfidenceStatus.EXPERIMENTAL
            reasons = ("no certified evaluations available",)
        elif count < 10:
            status = ModelConfidenceStatus.LIMITED_EVIDENCE
            reasons = ("fewer than 10 certified evaluations",)
        elif count < 30:
            status = ModelConfidenceStatus.DEVELOPING
            reasons = ("10 to 29 certified evaluations",)
        elif count < 100:
            status = ModelConfidenceStatus.TRUSTED
            reasons = ("30 to 99 certified evaluations",)
        else:
            status = ModelConfidenceStatus.ENTERPRISE_CERTIFIED
            reasons = ("100 or more certified evaluations",)

        return ModelConfidenceAssessment(
            registry_id=registry_entry.registry_id,
            model_name=registry_entry.model_name,
            model_version=registry_entry.model_version,
            forecast_horizon_days=statistics.forecast_horizon_days,
            confidence_status=status,
            eligible_evaluation_count=count,
            qualification_reasons=reasons,
        )

    @staticmethod
    def _validate_identity(
        registry_entry: ModelPerformanceRegistryEntry,
        statistics: ModelPerformanceStatistics,
    ) -> None:
        if (
            statistics.registry_id,
            statistics.model_name,
            statistics.model_version,
        ) != (
            registry_entry.registry_id,
            registry_entry.model_name,
            registry_entry.model_version,
        ):
            raise ValueError("statistics must match the registered model identity")
        if (
            statistics.forecast_horizon_days is not None
            and statistics.forecast_horizon_days not in registry_entry.supported_forecast_horizons
        ):
            raise ValueError("statistics horizon is not supported by the registered model version")
        if not statistics.advisory_only or not statistics.read_only:
            raise ValueError("statistics must remain advisory-only and read-only")
        if not statistics.inventory_source_of_truth_preserved:
            raise ValueError("inventory source of truth must be preserved")
