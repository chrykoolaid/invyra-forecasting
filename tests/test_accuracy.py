from datetime import date

import pytest

from invyra_forecasting.accuracy import AccuracyService, AccuracyValidationError, ActualDemandRecord, JsonlAccuracyStore, calculate_accuracy_metrics
from invyra_forecasting.config import ForecastingConfig
from invyra_forecasting.constants import Environment


def test_accuracy_metrics_rate_on_target_forecast_high():
    result = calculate_accuracy_metrics(
        forecast_quantity=21,
        actual_quantity=23,
        item_id="ITEM-001",
        location_id="LOC-001",
        environment=Environment.TRAINING,
        forecast_horizon_days=7,
        actual_record_count=7,
        forecast_snapshot_id="snapshot-1",
    )
    assert result.absolute_error == 2
    assert result.accuracy_rating == "High"
    assert result.bias == "On Target"
    assert result.mean_absolute_error == 2
    assert result.mean_absolute_percentage_error is not None


def test_accuracy_service_persists_and_reads_item_results(tmp_path):
    service = AccuracyService(ForecastingConfig(environment=Environment.TRAINING, accuracy_log_path=str(tmp_path / "accuracy.jsonl")))
    actuals = [
        ActualDemandRecord("ITEM-001", "LOC-001", date(2026, 6, 17), 3, Environment.TRAINING),
        ActualDemandRecord("ITEM-001", "LOC-001", date(2026, 6, 18), 4, Environment.TRAINING),
    ]
    result = service.evaluate(
        item_id="ITEM-001",
        location_id="LOC-001",
        environment=Environment.TRAINING,
        forecast_quantity=8,
        actuals=actuals,
        forecast_horizon_days=2,
        forecast_snapshot_id="snapshot-1",
        persist=True,
    )
    stored = JsonlAccuracyStore(tmp_path / "accuracy.jsonl").list_results(item_id="ITEM-001", environment=Environment.TRAINING)
    assert len(stored) == 1
    assert stored[0]["accuracy_id"] == result.accuracy_id
    assert stored[0]["actual_quantity"] == 7


def test_accuracy_service_blocks_mismatched_actuals():
    service = AccuracyService(ForecastingConfig(environment=Environment.TRAINING))
    actuals = [ActualDemandRecord("OTHER", "LOC-001", date(2026, 6, 17), 3, Environment.TRAINING)]
    with pytest.raises(AccuracyValidationError, match="actual item_id mismatch"):
        service.evaluate(
            item_id="ITEM-001",
            location_id="LOC-001",
            environment=Environment.TRAINING,
            forecast_quantity=8,
            actuals=actuals,
            forecast_horizon_days=2,
        )
