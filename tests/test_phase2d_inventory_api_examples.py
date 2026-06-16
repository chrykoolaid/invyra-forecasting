import json
from pathlib import Path

from invyra_forecasting.api.app import inventory_item_details_forecast
from invyra_forecasting.api.inventory_contracts import ItemDetailsForecastPanelRequest

EXAMPLES_DIR = Path(__file__).parents[1] / "examples" / "api" / "inventory_item_details"

REQUEST_EXAMPLES = {
    "item_details_forecast_request.json": "available",
    "item_details_forecast_request_low_confidence.json": "low_confidence",
    "item_details_forecast_request_unavailable.json": "unavailable",
}

PANEL_RESPONSE_EXAMPLES = {
    "item_details_forecast_response_available.json": "available",
    "item_details_forecast_response_low_confidence.json": "low_confidence",
    "item_details_forecast_response_unavailable.json": "unavailable",
}

REQUIRED_DISPLAY_FIELDS = {
    "forecast_demand_next_30_days",
    "average_daily_demand",
    "days_of_cover",
    "stockout_risk",
    "overstock_risk",
    "suggested_reorder_quantity",
    "confidence_rating",
    "confidence_score",
    "short_explanation",
    "last_snapshot_id",
    "generated_at_utc",
}


def _load_json(filename: str) -> dict:
    return json.loads((EXAMPLES_DIR / filename).read_text(encoding="utf-8"))


def _assert_advisory_flags(payload: dict) -> None:
    advisory = payload["advisory"]
    assert advisory["advisory_only"] is True
    assert advisory["inventory_ledger_source_of_truth"] is True
    assert advisory["mutates_stock"] is False
    assert advisory["creates_purchase_order"] is False
    assert advisory["approves_purchase_order"] is False


def _assert_fallback_contract(payload: dict) -> None:
    fallback = payload["fallback"]
    assert fallback["item_details_usable"] is True
    assert fallback["stock_history_usable"] is True
    assert fallback["manual_review_available"] is True


def test_phase2d_request_examples_validate_against_api_contract(monkeypatch, tmp_path):
    monkeypatch.setenv("INVYRA_FORECAST_SNAPSHOT_DIR", str(tmp_path / "snapshots"))
    monkeypatch.setenv("INVYRA_AUDIT_LOG_PATH", str(tmp_path / "audit" / "audit_events.jsonl"))
    monkeypatch.setenv("INVYRA_ACCURACY_LOG_PATH", str(tmp_path / "accuracy" / "accuracy_events.jsonl"))

    for filename, expected_status in REQUEST_EXAMPLES.items():
        request = ItemDetailsForecastPanelRequest(**_load_json(filename))
        response = inventory_item_details_forecast(request)
        assert response["status"] == expected_status
        assert response["panel"] == "inventory_item_details_forecast"
        _assert_advisory_flags(response)
        _assert_fallback_contract(response)
        if expected_status == "unavailable":
            assert response["display_fields"] is None
            assert response["snapshot_id"] is None
        else:
            assert response["display_fields"] is not None
            assert REQUIRED_DISPLAY_FIELDS.issubset(response["display_fields"].keys())


def test_phase2d_panel_response_examples_have_stable_contract_shape():
    for filename, expected_status in PANEL_RESPONSE_EXAMPLES.items():
        response = _load_json(filename)
        assert response["panel"] == "inventory_item_details_forecast"
        assert response["status"] == expected_status
        assert response["environment"] == "TRAINING"
        _assert_advisory_flags(response)
        _assert_fallback_contract(response)
        if expected_status == "unavailable":
            assert response["display_fields"] is None
            assert response["snapshot_id"] is None
            assert "Forecast unavailable" in response["message"]
        else:
            assert REQUIRED_DISPLAY_FIELDS.issubset(response["display_fields"].keys())
            assert response["snapshot_id"]
            assert response["display_fields"]["last_snapshot_id"] == response["snapshot_id"]


def test_phase2d_snapshot_response_examples_have_stable_contract_shape():
    available = _load_json("item_details_snapshot_response_available.json")
    assert available["status"] == "available"
    assert available["snapshot_id"] == available["snapshot"]["snapshot_id"]
    _assert_advisory_flags(available)
    assert available["snapshot"]["audit_event"]["details"]["advisory_only"] is True

    unavailable = _load_json("item_details_snapshot_response_unavailable.json")
    assert unavailable["status"] == "unavailable"
    assert unavailable["snapshot_id"] == "missing-snapshot"
    _assert_fallback_contract(unavailable)


def test_phase2d_readme_documents_required_endpoints_and_governance():
    readme = (EXAMPLES_DIR / "README.md").read_text(encoding="utf-8")
    assert "POST \"http://127.0.0.1:8000/inventory/item-details/forecast\"" in readme
    assert "GET /inventory/item-details/forecast/snapshots" not in readme  # curl form is documented instead
    assert "/inventory/item-details/forecast/snapshots/example-snapshot-id" in readme
    assert "advisory_only" in readme
    assert "mutate stock" in readme
    assert "Forecast unavailable. Item Details and stock history remain usable." in readme
