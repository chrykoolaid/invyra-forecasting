from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from invyra_forecasting.constants import Environment
from invyra_forecasting.models import (
    AdaptiveRankingConfiguration,
    AdaptiveRankingWeights,
    ForecastModelInput,
    ForecastModelOutput,
    ForecastModelOrchestrator,
    ForecastModelRegistry,
    ModelLifecycleStatus,
    ModelPerformanceRecord,
    ModelPerformanceRepository,
    ModelSelectionContext,
    PerformanceAwareModelSelector,
    RegisteredForecastModel,
)


@dataclass(frozen=True)
class DummyForecastModel:
    model_name: str
    model_version: str

    def forecast(self, model_input: ForecastModelInput, *, forecast_days: int = 30) -> ForecastModelOutput:
        return ForecastModelOutput(
            item_id=model_input.item_id,
            location_id=model_input.location_id,
            environment=model_input.environment,
            forecast_days=forecast_days,
            forecast_quantity=forecast_days * max(model_input.average_daily_demand, 0),
            projected_days_of_cover=None,
            stockout_risk="UNKNOWN",
            confidence=model_input.confidence,
            explanation=(f"{self.model_name} produced an advisory forecast.",),
            evidence_refs=model_input.evidence_refs,
            model_name=self.model_name,
            model_version=self.model_version,
        )


def _registered_model(model_id: str, *, name: str | None = None) -> RegisteredForecastModel:
    model = DummyForecastModel(model_name=name or model_id, model_version="7A.test")
    return RegisteredForecastModel(
        model_id=model_id,
        model_name=model.model_name,
        model_version=model.model_version,
        model=model,
        status=ModelLifecycleStatus.PRODUCTION,
        supported_forecast_types=("item_location_demand",),
        supported_horizons_days=(7, 14, 30, 60),
    )


def test_adaptive_model_ranking_selects_evidence_backed_model_over_static_order() -> None:
    registry = ForecastModelRegistry()
    static_first = _registered_model("static_first_model")
    adaptive_winner = _registered_model("adaptive_winner_model")
    registry.register(static_first)
    registry.register(adaptive_winner)

    repository = ModelPerformanceRepository(
        records=(
            ModelPerformanceRecord(
                model_id="static_first_model",
                accuracy=0.62,
                recent_accuracy=0.58,
                calibration=0.60,
                stability=0.60,
                evaluation_count=100,
                supported_contexts=("item_location_demand", "horizon:30"),
                horizon_accuracy={30: 0.60},
                bias=0.20,
                drift_score=0.20,
                data_sufficiency=0.90,
            ),
            ModelPerformanceRecord(
                model_id="adaptive_winner_model",
                accuracy=0.91,
                recent_accuracy=0.94,
                calibration=0.88,
                stability=0.86,
                evaluation_count=80,
                last_evaluated_at=datetime.now(timezone.utc).isoformat(),
                supported_contexts=(
                    "item_location_demand",
                    "horizon:30",
                    "category:grocery",
                    "location:store-1",
                    "season:summer",
                    "feature_backed",
                ),
                horizon_accuracy={30: 0.92},
                seasonal_accuracy={"summer": 0.90},
                bias=0.03,
                drift_score=0.04,
                data_sufficiency=0.95,
            ),
        )
    )
    orchestrator = ForecastModelOrchestrator(registry=registry, performance_repository=repository)

    selection = orchestrator.select_model(
        forecast_days=30,
        selection_context=ModelSelectionContext(
            forecast_type="item_location_demand",
            forecast_days=30,
            location_id="store-1",
            category_id="grocery",
            season_key="summer",
            evidence_count=4,
            feature_count=2,
        ),
    )

    assert selection.selected_model.model_id == "adaptive_winner_model"
    assert selection.candidate_scores[0].model_id == "adaptive_winner_model"
    assert selection.candidate_scores[0].score > selection.candidate_scores[1].score
    assert selection.audit_record is not None
    assert selection.audit_record.to_dict()["advisory_only"] is True
    assert selection.audit_record.to_dict()["read_only"] is True
    assert selection.audit_record.to_dict()["inventory_source_of_truth_preserved"] is True


def test_adaptive_ranking_is_deterministic_for_identical_inputs() -> None:
    models = (_registered_model("model_b"), _registered_model("model_a"))
    repository = ModelPerformanceRepository(
        records=(
            ModelPerformanceRecord(model_id="model_b", accuracy=0.80, calibration=0.80, stability=0.80, evaluation_count=40),
            ModelPerformanceRecord(model_id="model_a", accuracy=0.80, calibration=0.80, stability=0.80, evaluation_count=40),
        )
    )
    selector = PerformanceAwareModelSelector(repository)
    context = ModelSelectionContext(forecast_type="item_location_demand", forecast_days=30)

    first = selector.rank_models(models, context)
    second = selector.rank_models(models, context)

    assert [score.model_id for score in first] == [score.model_id for score in second]
    assert [score.model_id for score in first] == ["model_a", "model_b"]


def test_ranking_weights_are_configurable_without_code_changes() -> None:
    models = (_registered_model("accurate_model"), _registered_model("stable_model"))
    repository = ModelPerformanceRepository(
        records=(
            ModelPerformanceRecord(
                model_id="accurate_model",
                accuracy=0.95,
                recent_accuracy=0.95,
                calibration=0.60,
                stability=0.20,
                evaluation_count=50,
            ),
            ModelPerformanceRecord(
                model_id="stable_model",
                accuracy=0.70,
                recent_accuracy=0.70,
                calibration=0.80,
                stability=0.99,
                evaluation_count=50,
            ),
        )
    )
    stability_first_config = AdaptiveRankingConfiguration(
        version="7A.test.stability",
        weights=AdaptiveRankingWeights(
            accuracy=0.05,
            recent_accuracy=0.05,
            calibration=0.05,
            stability=0.70,
            bias_control=0.0,
            evaluation_depth=0.05,
            context_fit=0.05,
            horizon_fit=0.05,
            seasonality_fit=0.0,
            data_sufficiency=0.0,
            drift_resilience=0.0,
        ),
    )
    selector = PerformanceAwareModelSelector(repository, ranking_configuration=stability_first_config)

    ranked = selector.rank_models(models, ModelSelectionContext(forecast_type="item_location_demand", forecast_days=30))

    assert ranked[0].model_id == "stable_model"
    assert ranked[0].weight_version == "7A.test.stability"


def test_orchestrated_forecast_exposes_phase_7a_selection_metadata() -> None:
    registry = ForecastModelRegistry()
    registry.register(_registered_model("phase_7a_model", name="Phase 7A Model"))
    repository = ModelPerformanceRepository(
        records=(
            ModelPerformanceRecord(
                model_id="phase_7a_model",
                accuracy=0.90,
                recent_accuracy=0.90,
                calibration=0.90,
                stability=0.90,
                evaluation_count=60,
                supported_contexts=("item_location_demand", "horizon:30", "feature_backed"),
            ),
        )
    )
    model_input = ForecastModelInput(
        item_id="item-1",
        location_id="store-1",
        environment=Environment.TEST,
        analysis_window_days=30,
        average_daily_demand=2.0,
        latest_on_hand=10.0,
        confidence=0.8,
        evidence_refs=("evidence-1",),
        feature_summary={"category_id": "grocery", "season_key": "summer"},
    )

    class PassthroughHandoff:
        def from_intelligence(self, intelligence: object) -> ForecastModelInput:
            return model_input

    orchestrator = ForecastModelOrchestrator(
        registry=registry,
        performance_repository=repository,
        handoff_adapter=PassthroughHandoff(),  # type: ignore[arg-type]
    )

    result = orchestrator.forecast(object())  # type: ignore[arg-type]

    assert result.advisory_only is True
    assert result.inventory_source_of_truth_preserved is True
    assert result.orchestration_metadata["selection_policy"] in {
        "performance_aware",
        "adaptive_model_ranking_phase_7a",
    }
    assert result.orchestration_metadata["read_only"] is True
    assert result.selection.audit_record is not None
    assert result.selection.audit_record.ranking_configuration.version == "7A.1"
