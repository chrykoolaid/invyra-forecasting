from datetime import date, timedelta

from invyra_forecasting.config import ForecastingConfig
from invyra_forecasting.constants import Environment, MovementType
from invyra_forecasting.schemas import ForecastInputBundle, Item, Location, StockMovement, StockPosition, SupplierProfile
from invyra_forecasting.services.forecasting_service import ForecastingService
from invyra_forecasting.services.intelligence_forecasting import run_item_forecast_with_registry_intelligence
from invyra_forecasting.signals import InMemoryForecastSignalRegistry, make_location_stock_signal


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


def test_registry_intelligence_helper_attaches_context(tmp_path):
    registry = InMemoryForecastSignalRegistry()
    registry.publish(
        make_location_stock_signal(
            item_id="ITEM-001",
            sku="SKU-1",
            location_id="LOC-001",
            on_hand=20,
            evidence_ref="SNAPSHOT-001",
            environment=Environment.TEST,
            confidence=0.8,
        )
    )

    snapshot = run_item_forecast_with_registry_intelligence(
        _service(tmp_path),
        _bundle(),
        registry,
        actor="test",
        anchor_date=date(2026, 7, 3),
    )

    context = snapshot.intelligence_context
    assert context is not None
    assert context["item_id"] == "ITEM-001"
    assert context["location_id"] == "LOC-001"
    assert context["signal_count"] == 1
    assert context["feature_summary"]["latest_on_hand"] == 20
    assert context["governance"]["advisory_only"] is True
    assert snapshot.recommendation.item_id == "ITEM-001"
