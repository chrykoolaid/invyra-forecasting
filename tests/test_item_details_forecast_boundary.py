import json
from pathlib import Path

from invyra_forecasting.config import ForecastingConfig
from invyra_forecasting.constants import Environment
from invyra_forecasting.integrations.inventory import (
    LOW_CONFIDENCE_VERIFICATION_MESSAGE,
    ItemDetailsForecastBoundary,
)
from invyra_forecasting.services import ForecastingService

FIXTURE_PATH = Path(__file__).parents[1] / "integrations" / "inventory" / "fixtures" / "phase2a_item_details_source.json"


def _payload() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _boundary(tmp_path: Path) -> ItemDetailsForecastBoundary:
    config = ForecastingConfig(
        environment=Environment.TRAINING,
        snapshot_dir=str(tmp_path / "snapshots"),
        audit_log_path=str(tmp_path / "audit" / "audit_events.jsonl"),
        accuracy_log_path=str(tmp_path / "accuracy" / "accuracy_events.jsonl"),
    )
    return ItemDetailsForecastBoundary(service=ForecastingService(config))


def test_item_details_boundary_returns_clean_available_panel(tmp_path):
    payload = _payload()
    boundary = _boundary(tmp_path)

    panel = boundary.build_panel_from_mappings(
        item=payload["item"],
        location=payload["location"],
        stock_position=payload["stock_position"],
        movements=payload["movements"],
        supplier_profile=payload["supplier_profile"],
        environment=payload["environment"],
        actor=payload["actor"],
        anchor_date=payload["anchor_date"],
    )

    assert panel["panel"] == "inventory_item_details_forecast"
    assert panel["status"] == "available"
    assert panel["environment"] == "TRAINING"
    assert panel["item_id"] == "ITEM-001"
    assert panel["location_id"] == "BRANCH-001"
    assert panel["snapshot_id"]
    assert panel["snapshot_persisted"] is True
    assert panel["display_fields"]["forecast_demand_next_30_days"] > 0
    assert panel["display_fields"]["average_daily_demand"] > 0
    assert panel["display_fields"]["suggested_reorder_quantity"] >= 0
    assert panel["display_fields"]["confidence_rating"] in {"Medium", "High"}
    assert "movements" not in panel["display_fields"]
    assert panel["advisory"]["advisory_only"] is True
    assert panel["advisory"]["mutates_stock"] is False
    assert panel["advisory"]["creates_purchase_order"] is False
    assert panel["fallback"]["item_details_usable"] is True

    evidence = boundary.read_snapshot_evidence(panel["snapshot_id"])
    assert evidence["status"] == "available"
    assert evidence["snapshot_id"] == panel["snapshot_id"]


def test_item_details_boundary_shows_low_confidence_but_keeps_forecast_visible(tmp_path):
    payload = _payload()
    payload["supplier_profile"]["lead_time_variability"] = 3
    boundary = _boundary(tmp_path)

    panel = boundary.build_panel_from_mappings(
        item=payload["item"],
        location=payload["location"],
        stock_position=payload["stock_position"],
        movements=payload["movements"],
        supplier_profile=payload["supplier_profile"],
        environment=payload["environment"],
        actor=payload["actor"],
        anchor_date=payload["anchor_date"],
    )

    assert panel["status"] == "low_confidence"
    assert panel["display_fields"] is not None
    assert panel["display_fields"]["confidence_rating"] == "Low"
    assert LOW_CONFIDENCE_VERIFICATION_MESSAGE in panel["warnings"]
    assert panel["fallback"]["manual_review_available"] is True


def test_item_details_boundary_returns_unavailable_when_mapping_fails(tmp_path):
    payload = _payload()
    payload["stock_position"]["environment"] = "LIVE"
    boundary = _boundary(tmp_path)

    panel = boundary.build_panel_from_mappings(
        item=payload["item"],
        location=payload["location"],
        stock_position=payload["stock_position"],
        movements=payload["movements"],
        supplier_profile=payload["supplier_profile"],
        environment=payload["environment"],
        actor=payload["actor"],
        anchor_date=payload["anchor_date"],
    )

    assert panel["status"] == "unavailable"
    assert panel["display_fields"] is None
    assert panel["snapshot_id"] is None
    assert panel["snapshot_persisted"] is False
    assert "Forecast unavailable" in panel["message"]
    assert "environment mismatch" in panel["reason"]
    assert panel["fallback"]["item_details_usable"] is True
    assert panel["fallback"]["stock_history_usable"] is True
    assert panel["advisory"]["mutates_stock"] is False


def test_item_details_boundary_returns_unavailable_when_snapshot_missing(tmp_path):
    boundary = _boundary(tmp_path)

    evidence = boundary.read_snapshot_evidence("missing-snapshot")

    assert evidence["status"] == "unavailable"
    assert evidence["snapshot_id"] == "missing-snapshot"
    assert evidence["fallback"]["item_details_usable"] is True


class BrokenForecastingService:
    def __init__(self) -> None:
        self.snapshot_repository = object()

    def run_item_forecast(self, *args, **kwargs):
        raise RuntimeError("engine offline")

    def get_snapshot(self, snapshot_id: str):
        return None


def test_item_details_boundary_fails_closed_when_engine_errors():
    payload = _payload()
    boundary = ItemDetailsForecastBoundary(service=BrokenForecastingService())

    panel = boundary.build_panel_from_mappings(
        item=payload["item"],
        location=payload["location"],
        stock_position=payload["stock_position"],
        movements=payload["movements"],
        supplier_profile=payload["supplier_profile"],
        environment=payload["environment"],
        actor=payload["actor"],
        anchor_date=payload["anchor_date"],
    )

    assert panel["status"] == "unavailable"
    assert "engine offline" in panel["reason"]
    assert panel["fallback"]["item_details_usable"] is True
    assert panel["advisory"]["creates_purchase_order"] is False
