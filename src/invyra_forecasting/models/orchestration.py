from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Protocol

from invyra_forecasting.intelligence.objects import ForecastIntelligence
from invyra_forecasting.models.baseline import BaselineExplainableDemandModel
from invyra_forecasting.models.contracts import ForecastModelInput, ForecastModelOutput
from invyra_forecasting.models.handoff import ForecastModelHandoffAdapter
from invyra_forecasting.models.performance_selection import (
    AdaptiveRankingConfiguration,
    ModelPerformanceRepository,
    ModelPerformanceScore,
    ModelSelectionAuditRecord,
    ModelSelectionContext,
    PerformanceAwareModelSelector,
)


class ModelLifecycleStatus(StrEnum):
    """Lifecycle status used by the model orchestrator foundation."""

    TESTING = "TESTING"
    APPROVED = "APPROVED"
    PRODUCTION = "PRODUCTION"
    RETIRED = "RETIRED"


class ForecastModelProtocol(Protocol):
    """Minimal callable model protocol for orchestration."""

    model_name: str
    model_version: str

    def forecast(self, model_input: ForecastModelInput, *, forecast_days: int = 30) -> ForecastModelOutput:
        ...


@dataclass(frozen=True)
class RegisteredForecastModel:
    """Model registry entry available to the orchestrator."""

    model_id: str
    model_name: str
    model_version: str
    model: ForecastModelProtocol
    status: ModelLifecycleStatus = ModelLifecycleStatus.TESTING
    supported_forecast_types: tuple[str, ...] = ("item_location_demand",)
    supported_horizons_days: tuple[int, ...] = (7, 14, 30, 60, 90)
    strengths: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()

    def is_eligible(self, *, forecast_type: str, forecast_days: int) -> bool:
        return (
            self.status in {ModelLifecycleStatus.APPROVED, ModelLifecycleStatus.PRODUCTION}
            and forecast_type in self.supported_forecast_types
            and forecast_days in self.supported_horizons_days
        )

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload.pop("model")
        payload["status"] = self.status.value
        payload["supported_forecast_types"] = list(self.supported_forecast_types)
        payload["supported_horizons_days"] = list(self.supported_horizons_days)
        payload["strengths"] = list(self.strengths)
        payload["limitations"] = list(self.limitations)
        return payload


@dataclass(frozen=True)
class ModelSelectionResult:
    """Explainable model selection result."""

    selected_model: RegisteredForecastModel
    alternative_models_considered: tuple[RegisteredForecastModel, ...]
    selection_reasons: tuple[str, ...]
    warnings: tuple[str, ...] = ()
    candidate_scores: tuple[ModelPerformanceScore, ...] = ()
    audit_record: ModelSelectionAuditRecord | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "selected_model": self.selected_model.to_dict(),
            "alternative_models_considered": [model.to_dict() for model in self.alternative_models_considered],
            "selection_reasons": list(self.selection_reasons),
            "warnings": list(self.warnings),
            "candidate_scores": [score.to_dict() for score in self.candidate_scores],
            "audit_record": self.audit_record.to_dict() if self.audit_record else None,
        }


@dataclass(frozen=True)
class OrchestratedForecastResult:
    """Output from model orchestration."""

    model_output: ForecastModelOutput
    selection: ModelSelectionResult
    orchestration_metadata: dict[str, object] = field(default_factory=dict)

    @property
    def advisory_only(self) -> bool:
        return self.model_output.advisory_only

    @property
    def inventory_source_of_truth_preserved(self) -> bool:
        return self.model_output.inventory_source_of_truth_preserved

    def to_dict(self) -> dict[str, object]:
        return {
            "model_output": self.model_output.to_dict(),
            "selection": self.selection.to_dict(),
            "orchestration_metadata": dict(self.orchestration_metadata),
        }


class ForecastModelRegistry:
    """In-memory model registry used by the model orchestrator."""

    def __init__(self) -> None:
        self._models: dict[str, RegisteredForecastModel] = {}

    def register(self, model: RegisteredForecastModel) -> None:
        if model.model_id in self._models:
            raise ValueError(f"Model already registered: {model.model_id}")
        self._models[model.model_id] = model

    def all(self) -> tuple[RegisteredForecastModel, ...]:
        return tuple(self._models.values())

    def eligible(self, *, forecast_type: str, forecast_days: int) -> tuple[RegisteredForecastModel, ...]:
        return tuple(
            model for model in self._models.values() if model.is_eligible(forecast_type=forecast_type, forecast_days=forecast_days)
        )


def build_default_model_registry() -> ForecastModelRegistry:
    registry = ForecastModelRegistry()
    baseline = BaselineExplainableDemandModel()
    registry.register(
        RegisteredForecastModel(
            model_id="baseline_explainable_demand_model::2W.1",
            model_name=baseline.model_name,
            model_version=baseline.model_version,
            model=baseline,
            status=ModelLifecycleStatus.PRODUCTION,
            strengths=("deterministic", "explainable", "safe_baseline"),
            limitations=("not_advanced_ml", "limited_seasonality_awareness"),
        )
    )
    return registry


class ForecastModelOrchestrator:
    """Selects and runs eligible advisory forecast models."""

    def __init__(
        self,
        *,
        registry: ForecastModelRegistry | None = None,
        handoff_adapter: ForecastModelHandoffAdapter | None = None,
        performance_repository: ModelPerformanceRepository | None = None,
        model_selector: PerformanceAwareModelSelector | None = None,
        ranking_configuration: AdaptiveRankingConfiguration | None = None,
    ) -> None:
        self._registry = registry or build_default_model_registry()
        self._handoff_adapter = handoff_adapter or ForecastModelHandoffAdapter()
        self._model_selector = model_selector or PerformanceAwareModelSelector(
            performance_repository,
            ranking_configuration=ranking_configuration,
        )

    def select_model(
        self,
        *,
        forecast_type: str = "item_location_demand",
        forecast_days: int = 30,
        selection_context: ModelSelectionContext | None = None,
    ) -> ModelSelectionResult:
        eligible = self._registry.eligible(forecast_type=forecast_type, forecast_days=forecast_days)
        if not eligible:
            raise ValueError(f"No eligible forecast model for {forecast_type} over {forecast_days} days")

        context = selection_context or ModelSelectionContext(forecast_type=forecast_type, forecast_days=forecast_days)
        candidate_scores = self._model_selector.rank_models(eligible, context)
        selected_score = candidate_scores[0]
        model_by_id = {model.model_id: model for model in eligible}
        selected = model_by_id[selected_score.model_id]
        alternatives = tuple(model for model in eligible if model.model_id != selected.model_id)
        audit_record = self._model_selector.build_audit_record(
            selected_model_id=selected.model_id,
            candidate_scores=candidate_scores,
            context=context,
        )
        warnings = tuple(warning for score in candidate_scores for warning in score.warnings)
        return ModelSelectionResult(
            selected_model=selected,
            alternative_models_considered=alternatives,
            selection_reasons=(
                f"Selected {selected.model_name} version {selected.model_version} because it ranked highest for {forecast_type} over {forecast_days} days.",
                f"Winning adaptive ranking score was {selected_score.score:.6f}.",
                f"Ranking configuration version was {selected_score.weight_version}.",
                "Selection remained advisory-only and read-only.",
            ),
            warnings=warnings,
            candidate_scores=candidate_scores,
            audit_record=audit_record,
        )

    def forecast(
        self,
        intelligence: ForecastIntelligence,
        *,
        forecast_type: str = "item_location_demand",
        forecast_days: int = 30,
    ) -> OrchestratedForecastResult:
        model_input = self._handoff_adapter.from_intelligence(intelligence)
        selection_context = self._selection_context_from_model_input(
            model_input,
            forecast_type=forecast_type,
            forecast_days=forecast_days,
        )
        selection = self.select_model(
            forecast_type=forecast_type,
            forecast_days=forecast_days,
            selection_context=selection_context,
        )
        output = selection.selected_model.model.forecast(model_input, forecast_days=forecast_days)
        return OrchestratedForecastResult(
            model_output=output,
            selection=selection,
            orchestration_metadata={
                "forecast_type": forecast_type,
                "forecast_days": forecast_days,
                "eligible_model_count": 1 + len(selection.alternative_models_considered),
                "selection_policy": "performance_aware",
                "selection_policy_version": "adaptive_model_ranking_phase_7a",
                "ranking_configuration_version": selection.candidate_scores[0].weight_version if selection.candidate_scores else None,
                "advisory_only": output.advisory_only,
                "read_only": True,
                "inventory_source_of_truth_preserved": output.inventory_source_of_truth_preserved,
            },
        )

    def _selection_context_from_model_input(
        self,
        model_input: ForecastModelInput,
        *,
        forecast_type: str,
        forecast_days: int,
    ) -> ModelSelectionContext:
        feature_summary = model_input.feature_summary
        return ModelSelectionContext(
            forecast_type=forecast_type,
            forecast_days=forecast_days,
            average_daily_demand=model_input.average_daily_demand,
            latest_on_hand=model_input.latest_on_hand,
            confidence=model_input.confidence,
            evidence_count=len(model_input.evidence_refs),
            feature_count=len(model_input.engineered_features),
            item_id=model_input.item_id,
            location_id=model_input.location_id,
            category_id=feature_summary.get("category_id") if isinstance(feature_summary.get("category_id"), str) else None,
            season_key=feature_summary.get("season_key") if isinstance(feature_summary.get("season_key"), str) else None,
            demand_pattern=feature_summary.get("demand_pattern") if isinstance(feature_summary.get("demand_pattern"), str) else None,
        )
