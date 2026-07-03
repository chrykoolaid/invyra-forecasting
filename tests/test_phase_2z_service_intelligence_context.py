from datetime import date, timedelta

from invyra_forecasting.config import ForecastingConfig
from invyra_forecasting.constants import Environment, MovementType
from invyra_forecasting.schemas import ForecastInputBundle, Item, Location, StockMovement, StockPosition, SupplierProfile
from invyra_forecasting.services.forecasting_service import ForecastingService


def _bundle() -> ForecastInputBundle:
    today = date(2026, 7, 3)
    return ForecastInputBundle(
        item=Item(item_id="ITEM-001", sku="SKU-1", name="Test Item", category="General"),
        location=Location(location_id="LOC-001", name="Test Location"),
        stock_position=StockPosition(item_id="ITEM-001", location_id="LOC-001", on_hand=20, environment=Environment.TEST),
        movements=[
            StockMovement(
                movement_id="MOV-001",
                item_id="ITEM-001",
                location_id="LOC-001",
                movement_date=today - timedelta(days=1),
                movement_type=MovementType.POS_SALE,
                quantity=2,
                environment=Environment.TEST,
            )
        ],
        supplier_profile=SupplierProfile(supplier_id="SUP-001", item_id="ITEM-001", lead_time_days=3),
        environment=Environment.TEST,
    )


def _service(tmp_path) -> ForecastingService:
    return ForecastingService(
        ForecastingConfig(
            snapshot_dir=tmp_path / "snapshots",
            audit_log_path=tmp_path / "audit.jsonl",
            accuracy_log_path=tmp_path / "accuracy.jsonl",
        )
    )


def test_service_attaches_optional_intelligence_context(tmp_path):
    service = _service(tmp_path)
    context = {
        "signal_count": 2,
        "confidence": 0.75,
        "governance": {"advisory_only": True, "source_of_truth_preserved": True},
    }

    snapshot = service.run_item_forecast(
        _bundle(),
        actor="test",
        anchor_date=date(2026, 7, 3),
        intelligence_context=context,
    )

    assert snapshot.intelligence_context == context
    assert snapshot.to_dict()["intelligence_context"]["signal_count"] == 2
    assert snapshot.recommendation.item_id == "ITEM-001"


def test_service_default_forecast_flow_keeps_context_empty(tmp_path):
    service = _service(tmp_path)

    snapshot = service.run_item_forecast(_bundle(), actor="test", anchor_date=date(2026, 7, 3))

    assert snapshot.intelligence_context is None
    assert snapshot.to_dict()["intelligence_context"] is None
