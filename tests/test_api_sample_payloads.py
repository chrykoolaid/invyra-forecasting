import json
from pathlib import Path

from invyra_forecasting.api.app import audit_override, forecast_batch, forecast_item, reorder_recommendation, stockout_risk
from invyra_forecasting.api.contracts import BatchForecastRequest, ForecastRequest, OverrideAuditRequest

ROOT = Path(__file__).resolve().parents[1]
API_FIXTURES = ROOT / "data" / "sample" / "api"


def _json(name: str):
    return json.loads((API_FIXTURES / name).read_text(encoding="utf-8"))


def test_sample_forecast_item_payload_runs_engine():
    payload = ForecastRequest(**_json("forecast_item_request.json"))
    response = forecast_item(payload)
    assert response["forecast"]["item_id"] == "ITEM-001"
    assert response["forecast"]["forecast_quantity"] > 0
    assert response["confidence"]["rating"] in {"Low", "Medium", "High"}


def test_sample_stockout_risk_payload_returns_risk_block():
    payload = ForecastRequest(**_json("stockout_risk_request.json"))
    response = stockout_risk(payload)
    assert set(response) == {"risk", "confidence", "explanation"}
    assert response["risk"]["stockout_risk"] in {"Low", "Medium", "High"}


def test_sample_reorder_payload_returns_recommendation_block():
    payload = ForecastRequest(**_json("reorder_recommendation_request.json"))
    response = reorder_recommendation(payload)
    assert response["recommendation"]["reorder_needed"] is True
    assert response["recommendation"]["suggested_reorder_quantity"] > 0


def test_sample_batch_payload_returns_two_snapshots():
    payload = BatchForecastRequest(**_json("batch_forecast_request.json"))
    response = forecast_batch(payload)
    assert response["count"] == 2
    assert len(response["snapshots"]) == 2


def test_sample_override_payload_creates_override_audit_event():
    payload = OverrideAuditRequest(**_json("override_audit_request.json"))
    response = audit_override(payload)
    assert response["audit_event"]["event_type"] == "FORECAST_RECOMMENDATION_OVERRIDDEN"
    assert response["audit_event"]["details"]["override_action"] == "changed_quantity_to_18"


def test_module_fixture_pointers_reference_existing_payloads():
    module_fixture_paths = [
        ROOT / "integrations" / "inventory" / "fixtures" / "item_forecast_request.json",
        ROOT / "integrations" / "scanops" / "fixtures" / "stockout_risk_request.json",
        ROOT / "integrations" / "reorder_review" / "fixtures" / "reorder_recommendation_request.json",
        ROOT / "integrations" / "purchasing" / "fixtures" / "reorder_recommendation_request.json",
        ROOT / "integrations" / "dashboard" / "fixtures" / "batch_forecast_request.json",
        ROOT / "integrations" / "reports" / "fixtures" / "batch_forecast_request.json",
        ROOT / "integrations" / "suppliers" / "fixtures" / "supplier_lead_time_request.json",
        ROOT / "integrations" / "wastage" / "fixtures" / "wastage_demand_signal_request.json",
        ROOT / "integrations" / "pos" / "fixtures" / "pos_sales_signal_request.json",
    ]
    for path in module_fixture_paths:
        fixture = json.loads(path.read_text(encoding="utf-8"))
        assert fixture["payload_file"]
        assert (ROOT / fixture["payload_file"]).exists(), fixture
