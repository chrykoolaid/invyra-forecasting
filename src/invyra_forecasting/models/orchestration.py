from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Protocol

from invyra_forecasting.intelligence.objects import ForecastIntelligence
from invyra_forecasting.models.baseline import BaselineExplainableDemandModel
from invyra_forecasting.models.contracts import ForecastModelInput, ForecastModelOutput
from invyra_forecasting.models.handoff import ForecastModelHandoffAdapter


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

    def to_dict(self) -> dict[str, object]:
        return {
            "selected_model": self.selected_model.to_dict(),
            "alternative_models_considered": [model.to_dict() for model in self.alternative_models_considered],
            "selection_reasons": list(self.selection_reasons),
            "warnings": list(self.warnings),
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
    """In-memory model registry used by the Phase 5D orchestrator foundation."""

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
    """Selects and runs eligible advisory forecast models.

    The orchestrator does not mutate inventory, create stock movements, create
    purchase orders, approve purchase orders, or override ledger truth.
    """

    def __init__(
        self,
        *,
        registry: ForecastModelRegistry | None = None,
        handoff_adapter: ForecastModelHandoffAdapter | None = None,
    ) -> None:
        self._registry = registry or build_default_model_registry()
        self._handoff_adapter = handoff_adapter or ForecastModelHandoffAdapter()

    def select_model(self, *, forecast_type: str = "item_location_demand", forecast_days: int = 30) -> ModelSelectionResult:
        eligible = self._registry.eligible(forecast_type=forecast_type, forecast_days=forecast_days)
        if not eligible:
            raise ValueError(f"No eligible forecast model for {forecast_type} over {forecast_days} days")
        selected = eligible[0]
        alternatives = eligible[1:]
        return ModelSelectionResult(
            selected_model=selected,
            alternative_models_considered=alternatives,
            selection_reasons=(
                f"Selected {selected.model_name} version {selected.model_version} because it is eligible for {forecast_type} over {forecast_days} days.",
                "Phase 5D uses deterministic first-eligible selection until performance-aware orchestration is introduced.",
            ),
        )

    def forecast(
        self,
        intelligence: ForecastIntelligence,
        *,
        forecast_type: str = "item_location_demand",
        forecast_days: int = 30,
    ) -> OrchestratedForecastResult:
        selection = self.select_model(forecast_type=forecast_type, forecast_days=forecast_days)
        model_input = self._handoff_adapter.from_intelligence(intelligence)
        output = selection.selected_model.model.forecast(model_input, forecast_days=forecast_days)
        return OrchestratedForecastResult(
            model_output=output,
            selection=selection,
            orchestration_metadata={
                "forecast_type": forecast_type,
                "forecast_days": forecast_days,
                "eligible_model_count": 1 + len(selection.alternative_models_considered),
                "advisory_only": output.advisory_only,
                "inventory_source_of_truth_preserved": output.inventory_source_of_truth_preserved,
            },
        )
