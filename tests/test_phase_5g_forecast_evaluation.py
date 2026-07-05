import pytest

from invyra_forecasting.evaluation import ForecastEvaluationService, ForecastOutcome, ForecastPrediction
from invyra_forecasting.evaluation.metrics import ForecastEvaluationResult


def _prediction(forecast_id: str = "F1", predicted_quantity: float = 100, confidence: float = 0.8) -> ForecastPrediction:
    return ForecastPrediction(
        forecast_id=forecast_id,
        item_id="ITEM-1",
        location_id="LOC-1",
        model_name="baseline_explainable_demand_model",
        model_version="2W.1",
        forecast_horizon_days=30,
        predicted_quantity=predicted_quantity,
        confidence=confidence,
    )


def _outcome(forecast_id: str = "F1", actual_quantity: float = 80) -> ForecastOutcome:
    return ForecastOutcome(forecast_id=forecast_id, actual_quantity=actual_quantity)


def test_forecast_prediction_validates_values():
    with pytest.raises(ValueError):
        _prediction(predicted_quantity=-1)
    with pytest.raises(ValueError):
        _prediction(confidence=1.2)


def test_forecast_outcome_validates_values():
    with pytest.raises(ValueError):
        _outcome(actual_quantity=-1)


def test_forecast_evaluation_computes_metrics():
    result = ForecastEvaluationService().evaluate(_prediction(predicted_quantity=100), _outcome(actual_quantity=80))

    assert result.forecast_error == -20
    assert result.absolute_error == 20
    assert result.squared_error == 400
    assert result.absolute_percentage_error == 0.25
    assert result.bias == -20
    assert result.accuracy_score == 0.75
    assert result.calibration_gap == 0.05


def test_forecast_evaluation_rejects_mismatched_forecast_ids():
    with pytest.raises(ValueError):
        ForecastEvaluationService().evaluate(_prediction(forecast_id="F1"), _outcome(forecast_id="F2"))


def test_forecast_evaluation_handles_zero_actual_quantity():
    result = ForecastEvaluationService().evaluate(_prediction(predicted_quantity=0), _outcome(actual_quantity=0))

    assert result.absolute_percentage_error is None
    assert result.accuracy_score == 1.0


def test_forecast_evaluation_summary_computes_aggregate_metrics():
    service = ForecastEvaluationService()
    results = service.evaluate_many(
        (
            (_prediction("F1", 100), _outcome("F1", 80)),
            (_prediction("F2", 50), _outcome("F2", 60)),
        )
    )
    summary = service.summarize(results)

    assert summary["count"] == 2
    assert summary["mae"] == 15
    assert summary["rmse"] == 15.8114
    assert summary["mape"] == 0.2083
    assert summary["bias"] == -5


def test_forecast_evaluation_empty_summary_is_safe():
    summary = ForecastEvaluationService().summarize(())

    assert summary["count"] == 0
    assert summary["mae"] is None


def test_forecast_evaluation_preserves_guardrails():
    result = ForecastEvaluationService().evaluate(_prediction(), _outcome())
    payload = result.to_dict()

    assert payload["advisory_only"] is True
    assert payload["read_only"] is True
    assert payload["inventory_source_of_truth_preserved"] is True


def test_forecast_evaluation_rejects_guardrail_drift():
    with pytest.raises(ValueError):
        ForecastEvaluationResult(
            forecast_id="F1",
            item_id="ITEM-1",
            location_id="LOC-1",
            model_name="model",
            model_version="1",
            predicted_quantity=10,
            actual_quantity=10,
            forecast_error=0,
            absolute_error=0,
            squared_error=0,
            absolute_percentage_error=0,
            bias=0,
            accuracy_score=1,
            confidence=1,
            calibration_gap=0,
            read_only=False,
        )
