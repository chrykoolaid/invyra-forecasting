import json
from pathlib import Path

from invyra_forecasting.api.app import inventory_item_details_forecast, inventory_item_details_forecast_snapshot
from invyra_forecasting.api.inventory_contracts import ItemDetailsForecastPanelRequest

FIXTURE_PATH = Path(__file__).parents[1] / "integrations" / "inventory" / "fixtures" / "phase2a_item_details_source.json"


def _payload() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _request(payload: dict | None = None, **overrides) -> ItemDetailsForecastPanelRequest:
    data = payload or _payload()
    request_data = {
        "actor": data["actor"],
        "environment": data["environment"],
        "anchor_date": data["anchor_date"],
        "item": data["item"],
        "location": data["location"],
        "stock_position": data["stock_position"],
        "movements": data["movements"],
        "supplier_profile": data["supplier_profile"],
    }
    request_data.update(overrides)
    return ItemDetailsForecastPanelRequest(**request_data)


def _set_storage_env(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("INVYRA_FORECAST_SNAPSHOT_DIR", str(tmp_path / "snapshots"))
    monkeypatch.setenv("INVYRA_AUDIT_LOG_PATH", str(tmp_path / "audit" / "audit_events.jsonl"))
    monkeypatch.setenv("INVYRA_ACCURACY_LOG_PATH", str(tmp_path / "accuracy" / "accuracy_events.jsonl"))


def test_item_details_forecast_api_returns_available_panel(monkeypatch, tmp_path):
    _set_storage_env(monkeypatch, tmp_path)

    response = inventory_item_details_forecast(_request())

    assert response["panel"] == "inventory_item_details_forecast"
    assert response["status"] == "available"
    assert response["environment"] == "TRAINING"
    assert response["item_id"] == "ITEM-001"
    assert response["location_id"] == "BRANCH-001"
    assert response["snapshot_id"]
    assert response["snapshot_persisted"] is True
    assert response["display_fields"]["forecast_demand_next_30_days"] > 0
    assert response["display_fields"]["short_explanation"]
    assert response["advisory"]["advisory_only"] is True
    assert response["advisory"]["mutates_stock"] is False
    assert response["advisory"]["creates_purchase_order"] is False

    evidence = inventory_item_details_forecast_snapshot(response["snapshot_id"])
    assert evidence["status"] == "available"
    assert evidence["snapshot_id"] == response["snapshot_id"]


def test_item_details_forecast_api_preserves_unavailable_state(monkeypatch, tmp_path):
    _set_storage_env(monkeypatch, tmp_path)
    payload = _payload()
    payload["stock_position"]["environment"] = "LIVE"

    response = inventory_item_details_forecast(_request(payload))

    assert response["status"] == "unavailable"
    assert response["display_fields"] is None
    assert response["snapshot_id"] is None
    assert response["fallback"]["item_details_usable"] is True
    assert response["fallback"]["stock_history_usable"] is True
    assert "environment mismatch" in response["reason"]
    assert response["advisory"]["approves_purchase_order"] is False


def test_item_details_forecast_api_preserves_low_confidence_state(monkeypatch, tmp_path):
    _set_storage_env(monkeypatch, tmp_path)
    payload = _payload()
    payload["supplier_profile"]["lead_time_variability"] = 3

    response = inventory_item_details_forecast(_request(payload))

    assert response["status"] == "low_confidence"
    assert response["display_fields"] is not None
    assert response["display_fields"]["confidence_rating"] == "Low"
    assert any("Verify movement history" in warning for warning in response["warnings"])
    assert response["fallback"]["manual_review_available"] is True


def test_item_details_forecast_api_snapshot_missing_returns_safe_fallback(monkeypatch, tmp_path):
    _set_storage_env(monkeypatch, tmp_path)

    response = inventory_item_details_forecast_snapshot("missing-snapshot")

    assert response["status"] == "unavailable"
    assert response["snapshot_id"] == "missing-snapshot"
    assert response["fallback"]["item_details_usable"] is True


def test_item_details_forecast_api_can_skip_snapshot_persistence(monkeypatch, tmp_path):
    _set_storage_env(monkeypatch, tmp_path)

    response = inventory_item_details_forecast(_request(persist_snapshot=False))

    assert response["status"] == "available"
    assert response["snapshot_id"]
    assert response["snapshot_persisted"] is False
