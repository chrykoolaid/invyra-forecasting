from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable

from invyra_forecasting.evaluation.persistence import ForecastEvaluationRecord
from invyra_forecasting.evaluation_evidence_persistence import EvaluationEvidenceRecord
from invyra_forecasting.model_performance_registry import ModelPerformanceRegistryEntry
from invyra_forecasting.ranking_evidence_eligibility import RankingEvidenceEligibilityPolicy

MODEL_PERFORMANCE_STATISTICS_SCHEMA_VERSION = "1.0.0"


@dataclass(frozen=True)
class ModelPerformanceStatistics:
    registry_id: str
    model_name: str
    model_version: str
    forecast_horizon_days: int | None
    eligible_evaluation_count: int
    mae: float | None
    rmse: float | None
    mape: float | None
    bias: float | None
    average_accuracy_score: float | None
    average_calibration_gap: float | None
    schema_version: str = MODEL_PERFORMANCE_STATISTICS_SCHEMA_VERSION
    advisory_only: bool = True
    read_only: bool = True
    inventory_source_of_truth_preserved: bool = True

    def __post_init__(self) -> None:
        if not self.registry_id or not self.model_name or not self.model_version:
            raise ValueError("registry and model identity are required")
        if self.forecast_horizon_days is not None and self.forecast_horizon_days < 1:
            raise ValueError("forecast_horizon_days must be positive when provided")
        if self.eligible_evaluation_count < 0:
            raise ValueError("eligible_evaluation_count must not be negative")
        if self.schema_version != MODEL_PERFORMANCE_STATISTICS_SCHEMA_VERSION:
            raise ValueError("unsupported model performance statistics schema version")
        if not self.advisory_only or not self.read_only:
            raise ValueError("model performance statistics must remain advisory-only and read-only")
        if not self.inventory_source_of_truth_preserved:
            raise ValueError("inventory source of truth must be preserved")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ModelPerformanceStatisticsService:
    """Aggregates existing evaluation metrics from E7-certified evidence only."""

    def __init__(self, policy: RankingEvidenceEligibilityPolicy | None = None) -> None:
        self._policy = policy or RankingEvidenceEligibilityPolicy()

    def summarize(
        self,
        registry_entry: ModelPerformanceRegistryEntry,
        evidence_records: Iterable[EvaluationEvidenceRecord],
        evaluation_records: Iterable[ForecastEvaluationRecord],
        *,
        forecast_horizon_days: int | None = None,
    ) -> ModelPerformanceStatistics:
        if forecast_horizon_days is not None and forecast_horizon_days not in registry_entry.supported_forecast_horizons:
            raise ValueError("forecast horizon is not supported by the registered model version")

        evaluations = {record.evaluation_id: record for record in evaluation_records}
        accepted: list[ForecastEvaluationRecord] = []
        seen_evaluations: set[str] = set()

        for evidence in evidence_records:
            if evidence.namespace != registry_entry.namespace:
                continue
            decision = self._policy.assess(evidence)
            if not decision.eligible or evidence.evaluation_id in seen_evaluations:
                continue
            evaluation = evaluations.get(evidence.evaluation_id)
            if evaluation is None:
                continue
            self._validate_identity(registry_entry, evidence, evaluation)
            horizon = evaluation.result.evaluation_metadata.get("forecast_horizon_days")
            if forecast_horizon_days is not None and horizon != forecast_horizon_days:
                continue
            accepted.append(evaluation)
            seen_evaluations.add(evidence.evaluation_id)

        return self._build(registry_entry, accepted, forecast_horizon_days)

    @staticmethod
    def _validate_identity(
        registry_entry: ModelPerformanceRegistryEntry,
        evidence: EvaluationEvidenceRecord,
        evaluation: ForecastEvaluationRecord,
    ) -> None:
        linkage = evidence.linkage
        expected = (registry_entry.model_name, registry_entry.model_version)
        if (linkage.get("model_name"), linkage.get("model_version")) != expected:
            raise ValueError("certified evidence does not match the registered model version")
        if (evaluation.model_name, evaluation.model_version) != expected:
            raise ValueError("evaluation does not match the registered model version")
        if evaluation.evaluation_id != evidence.evaluation_id or evaluation.forecast_id != evidence.forecast_id:
            raise ValueError("evaluation and certified evidence identities must match")
        horizon = evaluation.result.evaluation_metadata.get("forecast_horizon_days")
        if horizon != linkage.get("forecast_horizon_days"):
            raise ValueError("evaluation and certified evidence horizons must match")
        if horizon not in registry_entry.supported_forecast_horizons:
            raise ValueError("certified evidence horizon is not supported by the registry entry")
        if not evaluation.advisory_only or not evaluation.read_only:
            raise ValueError("evaluation must remain advisory-only and read-only")
        if not evaluation.inventory_source_of_truth_preserved:
            raise ValueError("inventory source of truth must be preserved")

    @staticmethod
    def _build(
        registry_entry: ModelPerformanceRegistryEntry,
        records: list[ForecastEvaluationRecord],
        horizon: int | None,
    ) -> ModelPerformanceStatistics:
        if not records:
            return ModelPerformanceStatistics(
                registry_id=registry_entry.registry_id,
                model_name=registry_entry.model_name,
                model_version=registry_entry.model_version,
                forecast_horizon_days=horizon,
                eligible_evaluation_count=0,
                mae=None,
                rmse=None,
                mape=None,
                bias=None,
                average_accuracy_score=None,
                average_calibration_gap=None,
            )

        count = len(records)
        results = [record.result for record in records]
        ape_values = [result.absolute_percentage_error for result in results if result.absolute_percentage_error is not None]
        return ModelPerformanceStatistics(
            registry_id=registry_entry.registry_id,
            model_name=registry_entry.model_name,
            model_version=registry_entry.model_version,
            forecast_horizon_days=horizon,
            eligible_evaluation_count=count,
            mae=round(sum(result.absolute_error for result in results) / count, 4),
            rmse=round((sum(result.squared_error for result in results) / count) ** 0.5, 4),
            mape=None if not ape_values else round(sum(ape_values) / len(ape_values), 4),
            bias=round(sum(result.bias for result in results) / count, 4),
            average_accuracy_score=round(sum(result.accuracy_score for result in results) / count, 4),
            average_calibration_gap=round(sum(result.calibration_gap for result in results) / count, 4),
        )
