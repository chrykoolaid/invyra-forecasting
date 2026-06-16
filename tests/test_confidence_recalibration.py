from datetime import date, timedelta

from invyra_forecasting.accuracy import JsonlAccuracyStore, calculate_accuracy_metrics
from invyra_forecasting.config import ForecastingConfig
from invyra_forecasting.confidence import recalibrate_confidence_with_accuracy
from invyra_forecasting.constants import Environment, MovementType
from invyra_forecasting.schemas import ConfidenceResult, ForecastInputBundle, Item, Location, StockMovement, StockPosition, SupplierProfile
from invyra_forecasting.services import ForecastingService


def _bundle() -> ForecastInputBundle:
    start = date(2026, 5, 18)
    movements = [StockMovement(f"MOV-{idx}", "ITEM-001", "LOC-001", start + timedelta(days=idx), MovementType.POS_SALE, 2 if idx < 15 else 3, Environment.TRAINING) for idx in range(30)]
    return ForecastInputBundle(
        item=Item("ITEM-001", "SKU-1", "Coffee", "Grocery", minimum_order_quantity=6),
        location=Location("LOC-001", "Training Store"),
        stock_position=StockPosition("ITEM-001", "LOC-001", on_hand=10, environment=Environment.TRAINING),
        movements=movements,
        supplier_profile=SupplierProfile("SUP-001", "ITEM-001", lead_time_days=5, lead_time_variability_days=1, minimum_order_quantity=6),
        environment=Environment.TRAINING,
    )


def test_no_accuracy_history_leaves_confidence_unchanged():
    base = ConfidenceResult(rating="High", score=90, reasons=["Base confidence."])
    adjusted = recalibrate_confidence_with_accuracy(base, [], window=10)
    assert adjusted == base


def test_low_accuracy_history_reduces_confidence_and_explains_reason():
    base = ConfidenceResult(rating="High", score=90, reasons=["Base confidence."])
    history = [
        {"accuracy_score": 55, "bias": "Under Forecast"},
        {"accuracy_score": 50, "bias": "Under Forecast"},
        {"accuracy_score": 60, "bias": "Under Forecast"},
    ]
    adjusted = recalibrate_confidence_with_accuracy(base, history, window=10)
    assert adjusted.score < base.score
    assert adjusted.rating == "Medium"
    assert any("Weak historical forecast accuracy" in reason for reason in adjusted.reasons)
    assert any("Repeated under forecast bias" in reason for reason in adjusted.reasons)


def test_strong_accuracy_history_increases_confidence_slightly():
    base = ConfidenceResult(rating="Medium", score=70, reasons=["Base confidence."])
    history = [
        {"accuracy_score": 90, "bias": "On Target"},
        {"accuracy_score": 92, "bias": "On Target"},
    ]
    adjusted = recalibrate_confidence_with_accuracy(base, history, window=10)
    assert adjusted.score == 75
    assert adjusted.rating == "High"
    assert any("Strong historical forecast accuracy" in reason for reason in adjusted.reasons)


def test_forecasting_service_applies_accuracy_recalibration(tmp_path):
    accuracy_path = tmp_path / "accuracy_events.jsonl"
    store = JsonlAccuracyStore(accuracy_path)
    for idx in range(3):
        result = calculate_accuracy_metrics(
            forecast_quantity=30,
            actual_quantity=10,
            item_id="ITEM-001",
            location_id="LOC-001",
            environment=Environment.TRAINING,
            forecast_horizon_days=7,
            actual_record_count=7,
            forecast_snapshot_id=f"snapshot-{idx}",
        )
        store.append(result)

    service = ForecastingService(
        ForecastingConfig(
            environment=Environment.TRAINING,
            accuracy_log_path=str(accuracy_path),
            snapshot_dir=str(tmp_path / "snapshots"),
            audit_log_path=str(tmp_path / "audit.jsonl"),
            confidence_accuracy_window=10,
        )
    )
    snapshot = service.run_item_forecast(_bundle(), actor="confidence_test", anchor_date=date(2026, 6, 16))

    assert snapshot.confidence.score < 100
    assert any("Accuracy recalibration used" in reason for reason in snapshot.confidence.reasons)
    assert any("Weak historical forecast accuracy" in reason for reason in snapshot.confidence.reasons)
