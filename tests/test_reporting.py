from datetime import date, timedelta

from invyra_forecasting.accuracy import AccuracyService, ActualDemandRecord
from invyra_forecasting.audit import JsonlAuditStore, create_override_audit_event
from invyra_forecasting.config import ForecastingConfig
from invyra_forecasting.constants import Environment, MovementType
from invyra_forecasting.reporting import ReportService
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


def _config(tmp_path) -> ForecastingConfig:
    return ForecastingConfig(
        environment=Environment.TRAINING,
        snapshot_dir=str(tmp_path / "snapshots"),
        audit_log_path=str(tmp_path / "audit_events.jsonl"),
        accuracy_log_path=str(tmp_path / "accuracy_events.jsonl"),
        report_export_dir=str(tmp_path / "reports"),
    )


def test_report_summary_aggregates_snapshots_accuracy_and_audit(tmp_path):
    config = _config(tmp_path)
    ForecastingService(config).run_item_forecast(_bundle(), actor="report_test", anchor_date=date(2026, 6, 16), write_snapshot=True)
    AccuracyService(config).evaluate(
        item_id="ITEM-001",
        location_id="LOC-001",
        environment=Environment.TRAINING,
        forecast_quantity=21,
        actuals=[ActualDemandRecord("ITEM-001", "LOC-001", date(2026, 6, 17), 20, Environment.TRAINING)],
        forecast_horizon_days=1,
        forecast_snapshot_id="snapshot-1",
        persist=True,
    )
    JsonlAuditStore(config.audit_log_path).append(
        create_override_audit_event(
            actor="manager-1",
            environment=Environment.TRAINING,
            item_id="ITEM-001",
            location_id="LOC-001",
            original_recommendation={"suggested_reorder_quantity": 12},
            override_action="changed_quantity_to_18",
            reason="Supplier case pack changed.",
        )
    )

    summary = ReportService(config).build_summary(item_id="ITEM-001", location_id="LOC-001", environment="TRAINING")

    assert summary["snapshot_count"] == 1
    assert summary["accuracy_count"] == 1
    assert summary["audit_event_count"] == 2
    assert summary["average_accuracy_score"] is not None
    assert "FORECAST_CREATED" in summary["audit_event_counts"]


def test_report_service_exports_json_and_csv(tmp_path):
    config = _config(tmp_path)
    ForecastingService(config).run_item_forecast(_bundle(), actor="report_test", anchor_date=date(2026, 6, 16), write_snapshot=True)
    service = ReportService(config)

    json_result = service.export_report("summary", "json", item_id="ITEM-001", location_id="LOC-001", environment="TRAINING")
    csv_result = service.export_report("snapshots", "csv", item_id="ITEM-001", location_id="LOC-001", environment="TRAINING")

    assert json_result.path.endswith(".json")
    assert csv_result.path.endswith(".csv")
    assert json_result.row_count == 1
    assert csv_result.row_count == 1
