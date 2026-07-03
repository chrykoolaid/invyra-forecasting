from fastapi.testclient import TestClient

from invyra_forecasting.api.app import app


client = TestClient(app)


def _payload():
    return {
        "item_id": "ITEM-001",
        "location_id": "LOC-001",
        "environment": "TEST",
        "analysis_window_days": 30,
        "forecast_days": 14,
        "signals": [
            {
                "signal_id": "SIG-MOV-001",
                "signal_type": "SALE_EVENT",
                "module_source": "POS",
                "item_id": "ITEM-001",
                "sku": "SKU-1",
                "location_id": "LOC-001",
                "timestamp_utc": "2026-07-03T00:00:00Z",
                "quantity": 12,
                "unit": "unit",
                "direction": "OUTBOUND",
                "reason_code": "POS_SALE",
                "confidence": 0.95,
                "evidence_ref": "MOV-001",
                "environment": "TEST",
            },
            {
                "signal_id": "SIG-STOCK-001",
                "signal_type": "LOCATION_STOCK_EVENT",
                "module_source": "INVENTORY",
                "item_id": "ITEM-001",
                "sku": "SKU-1",
                "location_id": "LOC-001",
                "timestamp_utc": "2026-07-03T00:00:00Z",
                "quantity": 8,
                "unit": "unit",
                "direction": "NEUTRAL",
                "reason_code": "ON_HAND_SNAPSHOT",
                "confidence": 0.9,
                "evidence_ref": "SNAPSHOT-001",
                "environment": "TEST",
                "metadata": {"on_hand": 8},
            },
        ],
    }


def test_advisory_forecast_api_returns_explainable_response():
    response = client.post("/advisory/forecast", json=_payload())

    assert response.status_code == 200
    body = response.json()
    assert body["item_id"] == "ITEM-001"
    assert body["location_id"] == "LOC-001"
    assert body["environment"] == "TEST"
    assert body["forecast_days"] == 14
    assert body["forecast_quantity"] > 0
    assert body["stockout_risk"] in {"HIGH", "MEDIUM", "LOW", "UNKNOWN"}
    assert body["advisory_only"] is True
    assert body["inventory_source_of_truth_preserved"] is True
    assert body["intelligence_summary"]["signal_count"] == 2
    assert body["model_metadata"]["model_name"] == "baseline_explainable_demand_model"
    assert "MOV-001" in body["evidence_refs"]


def test_advisory_forecast_api_rejects_invalid_signal_contract():
    payload = _payload()
    payload["signals"][0]["confidence"] = 1.5

    response = client.post("/advisory/forecast", json=payload)

    assert response.status_code == 422


def test_advisory_forecast_api_empty_signals_is_safe():
    payload = {
        "item_id": "ITEM-MISSING",
        "location_id": "LOC-001",
        "environment": "TEST",
        "signals": [],
    }

    response = client.post("/advisory/forecast", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["forecast_quantity"] == 0
    assert body["stockout_risk"] == "UNKNOWN"
    assert body["evidence_refs"] == []
    assert body["advisory_only"] is True
