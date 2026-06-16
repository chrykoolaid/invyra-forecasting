from datetime import date, timedelta

from invyra_forecasting.audit import JsonlAuditStore, create_override_audit_event
from invyra_forecasting.config import ForecastingConfig
from invyra_forecasting.constants import Environment, MovementType
from invyra_forecasting.data.repositories import FileSnapshotRepository
from invyra_forecasting.schemas import ForecastInputBundle, Item, Location, StockMovement, StockPosition, SupplierProfile
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


def test_snapshot_repository_saves_and_reads_snapshot(tmp_path):
    snapshot_dir = tmp_path / "snapshots"
    audit_log_path = tmp_path / "audit" / "audit_events.jsonl"
    service = ForecastingService(ForecastingConfig(environment=Environment.TRAINING, snapshot_dir=str(snapshot_dir), audit_log_path=str(audit_log_path)))
    snapshot = service.run_item_forecast(_bundle(), actor="persistence_test", anchor_date=date(2026, 6, 16), write_snapshot=True)

    repository = FileSnapshotRepository(snapshot_dir)
    stored = repository.get(snapshot.snapshot_id)

    assert stored is not None
    assert stored["snapshot_id"] == snapshot.snapshot_id
    assert stored["forecast"]["item_id"] == "ITEM-001"
    assert repository.exists(snapshot.snapshot_id)
    assert snapshot.snapshot_id in repository.list_snapshot_ids()


def test_forecast_audit_event_is_persisted_when_snapshot_is_written(tmp_path):
    service = ForecastingService(
        ForecastingConfig(
            environment=Environment.TRAINING,
            snapshot_dir=str(tmp_path / "snapshots"),
            audit_log_path=str(tmp_path / "audit_events.jsonl"),
        )
    )
    snapshot = service.run_item_forecast(_bundle(), actor="persistence_test", anchor_date=date(2026, 6, 16), write_snapshot=True)

    events = JsonlAuditStore(tmp_path / "audit_events.jsonl").list_events(item_id="ITEM-001", environment=Environment.TRAINING)

    assert len(events) == 1
    assert events[0]["event_id"] == snapshot.audit_event.event_id
    assert events[0]["event_type"] == "FORECAST_CREATED"


def test_override_audit_event_store_filters_events(tmp_path):
    store = JsonlAuditStore(tmp_path / "audit_events.jsonl")
    event = create_override_audit_event(
        actor="manager-1",
        environment=Environment.TRAINING,
        item_id="ITEM-001",
        location_id="LOC-001",
        original_recommendation={"suggested_reorder_quantity": 12},
        override_action="changed_quantity_to_18",
        reason="Supplier case pack changed.",
    )

    store.append(event)
    events = store.list_events(event_type="FORECAST_RECOMMENDATION_OVERRIDDEN", item_id="ITEM-001", location_id="LOC-001", environment="TRAINING")

    assert len(events) == 1
    assert events[0]["details"]["override_action"] == "changed_quantity_to_18"
    assert events[0]["details"]["reason"] == "Supplier case pack changed."
