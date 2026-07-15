from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable

from invyra_forecasting.model_confidence_governance import ModelConfidenceAssessment
from invyra_forecasting.model_performance_registry import ModelPerformanceRegistryEntry
from invyra_forecasting.model_performance_statistics import ModelPerformanceStatistics

ADAPTIVE_SELECTION_INPUT_SCHEMA_VERSION = "1.0.0"


@dataclass(frozen=True)
class AdaptiveSelectionContext:
    forecast_horizon_days: int
    demand_profile: str | None = None
    season_key: str | None = None
    item_id: str | None = None
    location_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.forecast_horizon_days, int) or isinstance(
            self.forecast_horizon_days, bool
        ) or self.forecast_horizon_days < 1:
            raise ValueError("forecast_horizon_days must be a positive integer")
        for field_name in ("demand_profile", "season_key", "item_id", "location_id"):
            value = getattr(self, field_name)
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise ValueError(f"{field_name} must be a non-empty string when provided")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AdaptiveSelectionCandidateInput:
    registry_id: str
    model_name: str
    model_version: str
    lifecycle_status: str
    forecast_horizon_days: int
    horizon_supported: bool
    demand_profile: str | None
    demand_profile_supported: bool | None
    eligible_evaluation_count: int
    confidence_status: str
    mae: float | None
    rmse: float | None
    mape: float | None
    bias: float | None
    average_accuracy_score: float | None
    average_calibration_gap: float | None
    qualification_reasons: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    schema_version: str = ADAPTIVE_SELECTION_INPUT_SCHEMA_VERSION
    advisory_only: bool = True
    read_only: bool = True
    inventory_source_of_truth_preserved: bool = True

    def __post_init__(self) -> None:
        if not self.registry_id or not self.model_name or not self.model_version:
            raise ValueError("registry and model identity are required")
        if self.forecast_horizon_days < 1:
            raise ValueError("forecast_horizon_days must be positive")
        if self.eligible_evaluation_count < 0:
            raise ValueError("eligible_evaluation_count must not be negative")
        if not self.qualification_reasons:
            raise ValueError("qualification_reasons are required")
        if self.schema_version != ADAPTIVE_SELECTION_INPUT_SCHEMA_VERSION:
            raise ValueError("unsupported adaptive selection input schema version")
        if not self.advisory_only or not self.read_only:
            raise ValueError("adaptive selection inputs must remain advisory-only and read-only")
        if not self.inventory_source_of_truth_preserved:
            raise ValueError("inventory source of truth must be preserved")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["qualification_reasons"] = list(self.qualification_reasons)
        payload["evidence_refs"] = list(self.evidence_refs)
        return payload


@dataclass(frozen=True)
class AdaptiveSelectionInputPackage:
    context: AdaptiveSelectionContext
    candidates: tuple[AdaptiveSelectionCandidateInput, ...]
    schema_version: str = ADAPTIVE_SELECTION_INPUT_SCHEMA_VERSION
    advisory_only: bool = True
    read_only: bool = True
    inventory_source_of_truth_preserved: bool = True

    def __post_init__(self) -> None:
        if not self.candidates:
            raise ValueError("at least one adaptive selection candidate is required")
        identities = [
            (candidate.registry_id, candidate.model_name, candidate.model_version)
            for candidate in self.candidates
        ]
        if len(set(identities)) != len(identities):
            raise ValueError("adaptive selection candidates must be unique")
        if any(
            candidate.forecast_horizon_days != self.context.forecast_horizon_days
            for candidate in self.candidates
        ):
            raise ValueError("candidate horizons must match the selection context")
        if self.schema_version != ADAPTIVE_SELECTION_INPUT_SCHEMA_VERSION:
            raise ValueError("unsupported adaptive selection input package schema version")
        if not self.advisory_only or not self.read_only:
            raise ValueError("adaptive selection packages must remain advisory-only and read-only")
        if not self.inventory_source_of_truth_preserved:
            raise ValueError("inventory source of truth must be preserved")

    def to_dict(self) -> dict[str, Any]:
        return {
            "context": self.context.to_dict(),
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "schema_version": self.schema_version,
            "advisory_only": self.advisory_only,
            "read_only": self.read_only,
            "inventory_source_of_truth_preserved": self.inventory_source_of_truth_preserved,
        }


class AdaptiveSelectionInputBuilder:
    """Builds governed candidate evidence without scoring or selecting models."""

    def build_candidate(
        self,
        registry_entry: ModelPerformanceRegistryEntry,
        statistics: ModelPerformanceStatistics,
        confidence: ModelConfidenceAssessment,
        context: AdaptiveSelectionContext,
        *,
        evidence_refs: Iterable[str] = (),
    ) -> AdaptiveSelectionCandidateInput:
        self._validate_identity(registry_entry, statistics, confidence)
        refs = tuple(dict.fromkeys(ref.strip() for ref in evidence_refs))
        if any(not ref for ref in refs):
            raise ValueError("evidence_refs must contain non-empty strings")

        horizon_supported = (
            context.forecast_horizon_days in registry_entry.supported_forecast_horizons
        )
        if statistics.forecast_horizon_days is not None and (
            statistics.forecast_horizon_days != context.forecast_horizon_days
        ):
            raise ValueError("statistics horizon must match the selection context")
        if confidence.forecast_horizon_days is not None and (
            confidence.forecast_horizon_days != context.forecast_horizon_days
        ):
            raise ValueError("confidence horizon must match the selection context")

        profile_supported: bool | None = None
        if context.demand_profile is not None:
            profile_supported = (
                context.demand_profile in registry_entry.supported_demand_profiles
            )

        reasons = list(confidence.qualification_reasons)
        reasons.append(
            "forecast horizon is supported by the registered model version"
            if horizon_supported
            else "forecast horizon is not supported by the registered model version"
        )
        if profile_supported is not None:
            reasons.append(
                "demand profile is supported by the registered model version"
                if profile_supported
                else "demand profile is not supported by the registered model version"
            )

        return AdaptiveSelectionCandidateInput(
            registry_id=registry_entry.registry_id,
            model_name=registry_entry.model_name,
            model_version=registry_entry.model_version,
            lifecycle_status=registry_entry.lifecycle_status.value,
            forecast_horizon_days=context.forecast_horizon_days,
            horizon_supported=horizon_supported,
            demand_profile=context.demand_profile,
            demand_profile_supported=profile_supported,
            eligible_evaluation_count=statistics.eligible_evaluation_count,
            confidence_status=confidence.confidence_status.value,
            mae=statistics.mae,
            rmse=statistics.rmse,
            mape=statistics.mape,
            bias=statistics.bias,
            average_accuracy_score=statistics.average_accuracy_score,
            average_calibration_gap=statistics.average_calibration_gap,
            qualification_reasons=tuple(reasons),
            evidence_refs=refs,
        )

    def build_package(
        self,
        context: AdaptiveSelectionContext,
        candidates: Iterable[AdaptiveSelectionCandidateInput],
    ) -> AdaptiveSelectionInputPackage:
        return AdaptiveSelectionInputPackage(
            context=context,
            candidates=tuple(candidates),
        )

    @staticmethod
    def _validate_identity(
        registry_entry: ModelPerformanceRegistryEntry,
        statistics: ModelPerformanceStatistics,
        confidence: ModelConfidenceAssessment,
    ) -> None:
        expected = (
            registry_entry.registry_id,
            registry_entry.model_name,
            registry_entry.model_version,
        )
        if (
            statistics.registry_id,
            statistics.model_name,
            statistics.model_version,
        ) != expected:
            raise ValueError("statistics must match the registered model identity")
        if (
            confidence.registry_id,
            confidence.model_name,
            confidence.model_version,
        ) != expected:
            raise ValueError("confidence must match the registered model identity")
        if confidence.eligible_evaluation_count != statistics.eligible_evaluation_count:
            raise ValueError("confidence evidence count must match performance statistics")
        objects = (registry_entry, statistics, confidence)
        if any(not item.advisory_only or not item.read_only for item in objects):
            raise ValueError("adaptive selection inputs must remain advisory-only and read-only")
        if any(not item.inventory_source_of_truth_preserved for item in objects):
            raise ValueError("inventory source of truth must be preserved")
