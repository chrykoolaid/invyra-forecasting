from __future__ import annotations

from invyra_forecasting.models import (
    ForecastModelOrchestrator,
    ForecastModelRegistry,
    ModelLifecycleStatus,
    ModelPerformanceRecord,
    ModelPerformanceRepository,
    ModelSelectionContext,
    RegisteredForecastModel,
)
from invyra_forecasting.models.contracts import ForecastModelInput, ForecastModelOutput


class _DummyModel:
    def __init__(self, name: str, version: str) -> None:
        self.model_name = name
        self.model_version = version

    def forecast(self, model_input: ForecastModelInput, *, forecast_days: int = 30) -> ForecastModelOutput:
        raise AssertionError("selection tests should not execute dummy models")


def _registered_model(model_id: str, name: str) -> RegisteredForecastModel:
    model = _DummyModel(name, "6A.1")
    return RegisteredForecastModel(
        model_id=model_id,
        model_name=model.model_name,
        model_version=model.model_version,
        model=model,
        status=ModelLifecycleStatus.PRODUCTION,
        supported_forecast_types=("item_location_demand",),
        supported_horizons_days=(30,),
    )


def test_phase_6a_selects_highest_ranked_performance_model() -> None:
    registry = ForecastModelRegistry()
    weaker = _registered_model("model::weaker", "weaker_model")
    stronger = _registered_model("model::stronger", "stronger_model")
    registry.register(weaker)
    registry.register(stronger)

    performance_repository = ModelPerformanceRepository(
        (
            ModelPerformanceRecord(
                model_id="model::weaker",
                accuracy=0.60,
                calibration=0.60,
                stability=0.60,
                evaluation_count=40,
                supported_contexts=("item_location_demand", "horizon:30"),
            ),
            ModelPerformanceRecord(
                model_id="model::stronger",
                accuracy=0.92,
                calibration=0.88,
                stability=0.90,
                evaluation_count=80,
                supported_contexts=("item_location_demand", "horizon:30"),
            ),
        )
    )
    orchestrator = ForecastModelOrchestrator(registry=registry, performance_repository=performance_repository)

    selection = orchestrator.select_model(
        forecast_type="item_location_demand",
        forecast_days=30,
        selection_context=ModelSelectionContext(
            forecast_type="item_location_demand",
            forecast_days=30,
            evidence_count=3,
            feature_count=1,
        ),
    )

    assert selection.selected_model.model_id == "model::stronger"
    assert [score.model_id for score in selection.candidate_scores] == ["model::stronger", "model::weaker"]
    assert selection.candidate_scores[0].score > selection.candidate_scores[1].score
    assert selection.audit_record is not None
    assert selection.audit_record.selected_model_id == "model::stronger"


def test_phase_6a_selection_is_deterministic_for_identical_scores() -> None:
    registry = ForecastModelRegistry()
    beta = _registered_model("model::beta", "beta_model")
    alpha = _registered_model("model::alpha", "alpha_model")
    registry.register(beta)
    registry.register(alpha)

    performance_repository = ModelPerformanceRepository(
        (
            ModelPerformanceRecord(model_id="model::alpha", accuracy=0.8, calibration=0.8, stability=0.8, evaluation_count=50),
            ModelPerformanceRecord(model_id="model::beta", accuracy=0.8, calibration=0.8, stability=0.8, evaluation_count=50),
        )
    )
    orchestrator = ForecastModelOrchestrator(registry=registry, performance_repository=performance_repository)

    first = orchestrator.select_model(forecast_type="item_location_demand", forecast_days=30)
    second = orchestrator.select_model(forecast_type="item_location_demand", forecast_days=30)

    assert first.selected_model.model_id == "model::alpha"
    assert second.selected_model.model_id == "model::alpha"
    assert [score.to_dict() for score in first.candidate_scores] == [
        score.to_dict() for score in second.candidate_scores
    ]


def test_phase_6a_selection_audit_preserves_governance_flags() -> None:
    registry = ForecastModelRegistry()
    model = _registered_model("model::safe", "safe_model")
    registry.register(model)
    orchestrator = ForecastModelOrchestrator(registry=registry)

    selection = orchestrator.select_model(forecast_type="item_location_demand", forecast_days=30)

    assert selection.audit_record is not None
    audit_payload = selection.audit_record.to_dict()
    assert audit_payload["advisory_only"] is True
    assert audit_payload["inventory_source_of_truth_preserved"] is True
    assert selection.warnings == ("No historical performance record exists for this model; neutral defaults were used.",)
    assert any("did not mutate inventory" in reason for reason in selection.selection_reasons)
