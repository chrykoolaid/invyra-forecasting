from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Iterable

from invyra_forecasting.api.tenant_namespace import current_namespace
from invyra_forecasting.model_confidence_governance import (
    ModelConfidenceAssessment,
    ModelConfidenceStatus,
)
from invyra_forecasting.model_performance_registry import ModelPerformanceRegistryEntry
from invyra_forecasting.model_performance_statistics import ModelPerformanceStatistics

ENTERPRISE_INTELLIGENCE_SUMMARY_SCHEMA_VERSION = "1.0.0"


@dataclass(frozen=True)
class EnterpriseModelIntelligenceInput:
    registry_entry: ModelPerformanceRegistryEntry
    statistics: ModelPerformanceStatistics
    confidence: ModelConfidenceAssessment
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        expected = (
            self.registry_entry.registry_id,
            self.registry_entry.model_name,
            self.registry_entry.model_version,
        )
        if (
            self.statistics.registry_id,
            self.statistics.model_name,
            self.statistics.model_version,
        ) != expected:
            raise ValueError("statistics must match the registered model identity")
        if (
            self.confidence.registry_id,
            self.confidence.model_name,
            self.confidence.model_version,
        ) != expected:
            raise ValueError("confidence must match the registered model identity")
        if self.statistics.forecast_horizon_days != self.confidence.forecast_horizon_days:
            raise ValueError("statistics and confidence horizons must match")
        if self.statistics.eligible_evaluation_count != self.confidence.eligible_evaluation_count:
            raise ValueError("statistics and confidence evidence counts must match")
        if self.statistics.eligible_evaluation_count > 0 and not self.evidence_refs:
            raise ValueError("evaluated models require evidence references")
        if any(not isinstance(ref, str) or not ref.strip() for ref in self.evidence_refs):
            raise ValueError("evidence references must contain non-empty strings")
        if len(set(self.evidence_refs)) != len(self.evidence_refs):
            raise ValueError("evidence references must be unique")
        guarded = (self.registry_entry, self.statistics, self.confidence)
        if any(not item.advisory_only or not item.read_only for item in guarded):
            raise ValueError("enterprise intelligence inputs must remain advisory-only and read-only")
        if any(not item.inventory_source_of_truth_preserved for item in guarded):
            raise ValueError("inventory source of truth must be preserved")


@dataclass(frozen=True)
class EnterpriseModelIntelligence:
    registry_id: str
    model_name: str
    model_version: str
    lifecycle_status: str
    forecast_horizon_days: int | None
    confidence_status: str
    eligible_evaluation_count: int
    average_accuracy_score: float | None
    average_calibration_gap: float | None
    bias: float | None
    evidence_refs: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["evidence_refs"] = list(self.evidence_refs)
        return payload


@dataclass(frozen=True)
class EnterpriseForecastIntelligenceSummary:
    namespace: str
    as_of_utc: str
    model_version_count: int
    evaluated_model_version_count: int
    total_eligible_evaluation_count: int
    confidence_distribution: dict[str, int]
    weighted_average_accuracy_score: float | None
    weighted_average_calibration_gap: float | None
    models: tuple[EnterpriseModelIntelligence, ...]
    schema_version: str = ENTERPRISE_INTELLIGENCE_SUMMARY_SCHEMA_VERSION
    advisory_only: bool = True
    read_only: bool = True
    inventory_source_of_truth_preserved: bool = True

    def __post_init__(self) -> None:
        if not self.namespace:
            raise ValueError("namespace is required")
        _parse_timestamp(self.as_of_utc)
        if self.model_version_count != len(self.models):
            raise ValueError("model_version_count must match the model summaries")
        if self.evaluated_model_version_count < 0 or self.total_eligible_evaluation_count < 0:
            raise ValueError("enterprise intelligence counts must not be negative")
        if self.schema_version != ENTERPRISE_INTELLIGENCE_SUMMARY_SCHEMA_VERSION:
            raise ValueError("unsupported enterprise intelligence summary schema version")
        if not self.advisory_only or not self.read_only:
            raise ValueError("enterprise intelligence summaries must remain advisory-only and read-only")
        if not self.inventory_source_of_truth_preserved:
            raise ValueError("inventory source of truth must be preserved")

    def to_dict(self) -> dict[str, Any]:
        return {
            "namespace": self.namespace,
            "as_of_utc": self.as_of_utc,
            "model_version_count": self.model_version_count,
            "evaluated_model_version_count": self.evaluated_model_version_count,
            "total_eligible_evaluation_count": self.total_eligible_evaluation_count,
            "confidence_distribution": dict(self.confidence_distribution),
            "weighted_average_accuracy_score": self.weighted_average_accuracy_score,
            "weighted_average_calibration_gap": self.weighted_average_calibration_gap,
            "models": [model.to_dict() for model in self.models],
            "schema_version": self.schema_version,
            "advisory_only": self.advisory_only,
            "read_only": self.read_only,
            "inventory_source_of_truth_preserved": self.inventory_source_of_truth_preserved,
        }


class EnterpriseForecastIntelligenceSummaryService:
    """Aggregates certified model intelligence without ranking or recommending actions."""

    def summarize(
        self,
        inputs: Iterable[EnterpriseModelIntelligenceInput],
        *,
        as_of_utc: str,
    ) -> EnterpriseForecastIntelligenceSummary:
        normalized_as_of = _parse_timestamp(as_of_utc).isoformat()
        namespace = current_namespace()
        items = tuple(inputs)
        identities: set[tuple[str, int | None]] = set()
        models: list[EnterpriseModelIntelligence] = []
        confidence_distribution = {status.value: 0 for status in ModelConfidenceStatus}

        for item in items:
            if item.registry_entry.namespace != namespace:
                raise ValueError("model registry namespace must match the active tenant namespace")
            identity = (item.registry_entry.registry_id, item.statistics.forecast_horizon_days)
            if identity in identities:
                raise ValueError("enterprise intelligence inputs must be unique by registry and horizon")
            identities.add(identity)
            confidence_distribution[item.confidence.confidence_status.value] += 1
            models.append(
                EnterpriseModelIntelligence(
                    registry_id=item.registry_entry.registry_id,
                    model_name=item.registry_entry.model_name,
                    model_version=item.registry_entry.model_version,
                    lifecycle_status=item.registry_entry.lifecycle_status.value,
                    forecast_horizon_days=item.statistics.forecast_horizon_days,
                    confidence_status=item.confidence.confidence_status.value,
                    eligible_evaluation_count=item.statistics.eligible_evaluation_count,
                    average_accuracy_score=item.statistics.average_accuracy_score,
                    average_calibration_gap=item.statistics.average_calibration_gap,
                    bias=item.statistics.bias,
                    evidence_refs=item.evidence_refs,
                )
            )

        ordered_models = tuple(
            sorted(
                models,
                key=lambda model: (
                    model.model_name,
                    model.model_version,
                    model.forecast_horizon_days or 0,
                    model.registry_id,
                ),
            )
        )
        total_evaluations = sum(model.eligible_evaluation_count for model in ordered_models)
        evaluated_count = sum(model.eligible_evaluation_count > 0 for model in ordered_models)

        return EnterpriseForecastIntelligenceSummary(
            namespace=namespace,
            as_of_utc=normalized_as_of,
            model_version_count=len(ordered_models),
            evaluated_model_version_count=evaluated_count,
            total_eligible_evaluation_count=total_evaluations,
            confidence_distribution=confidence_distribution,
            weighted_average_accuracy_score=_weighted_average(
                ordered_models,
                "average_accuracy_score",
            ),
            weighted_average_calibration_gap=_weighted_average(
                ordered_models,
                "average_calibration_gap",
            ),
            models=ordered_models,
        )


def _weighted_average(
    models: tuple[EnterpriseModelIntelligence, ...],
    field_name: str,
) -> float | None:
    measured = tuple(
        model
        for model in models
        if getattr(model, field_name) is not None and model.eligible_evaluation_count > 0
    )
    denominator = sum(model.eligible_evaluation_count for model in measured)
    if denominator == 0:
        return None
    numerator = sum(
        float(getattr(model, field_name)) * model.eligible_evaluation_count
        for model in measured
    )
    return round(numerator / denominator, 4)


def _parse_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("as_of_utc must be a valid ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("as_of_utc must include a UTC offset")
    return parsed
