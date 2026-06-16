from datetime import date, timedelta

from invyra_forecasting.config import ForecastingConfig
from invyra_forecasting.constants import Environment, MovementType
from invyra_forecasting.schemas import ForecastInputBundle, Item, Location, StockMovement, StockPosition, SupplierProfile
from invyra_forecasting.services import ForecastingService


def _bundle(on_hand: float = 10) -> ForecastInputBundle:
    start = date(2026, 5, 18)
    movements = [StockMovement(f"MOV-{idx}", "ITEM-001", "LOC-001", start + timedelta(days=idx), MovementType.POS_SALE, 2 if idx < 15 else 3, Environment.TRAINING) for idx in range(30)]
    return ForecastInputBundle(
        item=Item("ITEM-001", "SKU-1", "Coffee", "Grocery", minimum_order_quantity=6),
        location=Location("LOC-001", "Training Store"),
        stock_position=StockPosition("ITEM-001", "LOC-001", on_hand=on_hand, environment=Environment.TRAINING),
        movements=movements,
        supplier_profile=SupplierProfile("SUP-001", "ITEM-001", lead_time_days=5, lead_time_variability_days=1, minimum_order_quantity=6),
        environment=Environment.TRAINING,
    )


def test_item_forecast_produces_governed_outputs():
    service = ForecastingService(ForecastingConfig(environment=Environment.TRAINING))
    snapshot = service.run_item_forecast(_bundle(on_hand=10), actor="test", anchor_date=date(2026, 6, 16))
    assert snapshot.forecast.item_id == "ITEM-001"
    assert snapshot.forecast.forecast_quantity > 0
    assert snapshot.risk.stockout_risk in {"Low", "Medium", "High"}
    assert snapshot.recommendation.suggested_reorder_quantity % 6 == 0
    assert snapshot.confidence.rating in {"Low", "Medium", "High"}
    assert snapshot.explanation.summary
    assert snapshot.audit_event.event_type == "FORECAST_CREATED"
    assert snapshot.audit_event.details["advisory_only"] is True


def test_low_stock_triggers_reorder():
    service = ForecastingService(ForecastingConfig(environment=Environment.TRAINING))
    snapshot = service.run_item_forecast(_bundle(on_hand=2), actor="test", anchor_date=date(2026, 6, 16))
    assert snapshot.recommendation.reorder_needed is True
    assert snapshot.recommendation.urgency in {"Medium", "High"}
    assert snapshot.recommendation.suggested_reorder_quantity > 0
