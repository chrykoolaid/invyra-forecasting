from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from invyra_forecasting.models import (
    AdaptiveRankingConfiguration,
    AdaptiveRankingWeights,
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
class NeverCalledForecastModel:
    """Minimal model stub used only for selection tests."""

    model_name: str
    model_version: str

    def forecast(self, *args: object, **kwargs: object) -> object:
        raise AssertionError("Phase 7A selector tests must not execute forecast models")


def _registered_model(model_id: str, *, name: str | None = None) -> RegisteredForecastModel:
    model = NeverCalledForecastModel(model_name=name or model_id, model_version="7A.test")
    return RegisteredForecastModel(
        model_id=model_id,
        model_name=model.model_name,
        model_version=model.model_version,
        model=model,  # type: ignore[arg-type]
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
    audit_payload = selection.audit_record.to_dict()
    assert audit_payload["advisory_only"] is True
    assert audit_payload["read_only"] is True
    assert audit_payload["inventory_source_of_truth_preserved"] is True


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


def test_adaptive_ranking_audit_record_contains_configuration_and_guardrails() -> None:
    model = _registered_model("phase_7a_model", name="Phase 7A Model")
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
    selector = PerformanceAwareModelSelector(repository)
    context = ModelSelectionContext(
        forecast_type="item_location_demand",
        forecast_days=30,
        evidence_count=1,
        feature_count=1,
    )

    scores = selector.rank_models((model,), context)
    audit_record = selector.build_audit_record(
        selected_model_id="phase_7a_model",
        candidate_scores=scores,
        context=context,
    )
    audit_payload = audit_record.to_dict()

    assert audit_record.ranking_configuration.version == "7A.1"
    assert audit_payload["advisory_only"] is True
    assert audit_payload["read_only"] is True
    assert audit_payload["inventory_source_of_truth_preserved"] is True
    assert audit_payload["ranking_configuration"]["version"] == "7A.1"
