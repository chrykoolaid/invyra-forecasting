from __future__ import annotations

from datetime import date, timedelta

from fastapi.testclient import TestClient

from invyra_forecasting.api.app import app
from invyra_forecasting.api.contracts import ForecastRequest, ItemPayload, LocationPayload, StockMovementPayload, StockPositionPayload, SupplierProfilePayload
from invyra_forecasting.constants import Environment, MovementType


def _request() -> dict:
    start = date(2026, 5, 18)
    movements = [
        StockMovementPayload(
            movement_id=f"A3-MOV-{idx}",
            item_id="A3-ITEM-001",
            location_id="A3-LOC-001",
            movement_date=start + timedelta(days=idx),
            movement_type=MovementType.POS_SALE,
            quantity=2,
            environment=Environment.TRAINING,
        ).model_dump(mode="json")
        for idx in range(30)
    ]
    return ForecastRequest(
        actor="program_a3_test",
        environment=Environment.TRAINING,
        anchor_date=date(2026, 6, 16),
        write_snapshot=False,
        item=ItemPayload(item_id="A3-ITEM-001", sku="A3-SKU-1", name="Coffee", category="Grocery", minimum_order_quantity=6),
        location=LocationPayload(location_id="A3-LOC-001", name="Training Store"),
        stock_position=StockPositionPayload(item_id="A3-ITEM-001", location_id="A3-LOC-001", on_hand=10, environment=Environment.TRAINING),
        movements=movements,
        supplier_profile=SupplierProfilePayload(supplier_id="A3-SUP-001", item_id="A3-ITEM-001", lead_time_days=5, lead_time_variability_days=1, minimum_order_quantity=6),
    ).model_dump(mode="json")


def _client() -> TestClient:
    return TestClient(app)


def test_v1_metadata_includes_enterprise_forecast_compare_endpoint() -> None:
    payload = _client().get("/v1").json()

    assert "/v1/forecast/compare" in payload["data"]["stable_resources"]
    assert payload["advisory_only"] is True
    assert payload["read_only"] is True
    assert payload["inventory_source_of_truth_preserved"] is True


def test_v1_forecast_compare_returns_read_only_advisory_comparison() -> None:
    response = _client().post("/v1/forecast/compare", json=_request())

    assert response.status_code == 200
    payload = response.json()
    data = payload["data"]

    assert payload["resource"] == "forecast_comparison"
    assert payload["advisory_only"] is True
    assert payload["read_only"] is True
    assert payload["inventory_source_of_truth_preserved"] is True
    assert payload["metadata"]["write_snapshot"] is False

    assert data["advisory_only"] is True
    assert data["read_only"] is True
    assert data["inventory_source_of_truth_preserved"] is True
    assert data["comparison_strategy"] == "single_candidate_baseline_compare"
    assert data["recommended_model"] == data["candidates"][0]["model_id"]
    assert data["candidates"][0]["rank"] == 1
    assert data["candidates"][0]["selected"] is True
    assert data["candidates"][0]["forecast_quantity"] > 0
    assert 0 <= data["candidates"][0]["confidence_score"] <= 1
    assert data["forecast_snapshot"]["audit_event"]["details"]["advisory_only"] is True
