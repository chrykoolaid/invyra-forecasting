from __future__ import annotations

from datetime import date, timedelta

from fastapi.testclient import TestClient

from invyra_forecasting.api.app import app
from invyra_forecasting.api.contracts import ForecastRequest, ItemPayload, LocationPayload, StockMovementPayload, StockPositionPayload, SupplierProfilePayload
from invyra_forecasting.constants import Environment, MovementType


def _request(on_hand: float = 10) -> dict:
    start = date(2026, 5, 18)
    movements = [
        StockMovementPayload(
            movement_id=f"A2-MOV-{idx}",
            item_id="A2-ITEM-001",
            location_id="A2-LOC-001",
            movement_date=start + timedelta(days=idx),
            movement_type=MovementType.POS_SALE,
            quantity=2,
            environment=Environment.TRAINING,
        ).model_dump(mode="json")
        for idx in range(30)
    ]
    return ForecastRequest(
        actor="program_a2_test",
        environment=Environment.TRAINING,
        anchor_date=date(2026, 6, 16),
        write_snapshot=False,
        item=ItemPayload(item_id="A2-ITEM-001", sku="A2-SKU-1", name="Coffee", category="Grocery", minimum_order_quantity=6),
        location=LocationPayload(location_id="A2-LOC-001", name="Training Store"),
        stock_position=StockPositionPayload(item_id="A2-ITEM-001", location_id="A2-LOC-001", on_hand=on_hand, environment=Environment.TRAINING),
        movements=movements,
        supplier_profile=SupplierProfilePayload(supplier_id="A2-SUP-001", item_id="A2-ITEM-001", lead_time_days=5, lead_time_variability_days=1, minimum_order_quantity=6),
    ).model_dump(mode="json")


def _client() -> TestClient:
    return TestClient(app)


def test_v1_metadata_includes_enterprise_forecast_aliases() -> None:
    payload = _client().get("/v1").json()

    assert "/v1/forecast" in payload["data"]["stable_resources"]
    assert "/v1/forecast/batch" in payload["data"]["stable_resources"]
    assert payload["advisory_only"] is True
    assert payload["read_only"] is True
    assert payload["inventory_source_of_truth_preserved"] is True


def test_v1_forecast_alias_runs_existing_read_only_forecast_contract() -> None:
    response = _client().post("/v1/forecast", json=_request(on_hand=10))

    assert response.status_code == 200
    payload = response.json()

    assert payload["resource"] == "forecast_snapshot"
    assert payload["advisory_only"] is True
    assert payload["read_only"] is True
    assert payload["inventory_source_of_truth_preserved"] is True
    assert payload["metadata"]["write_snapshot"] is False
    assert payload["data"]["forecast"]["forecast_quantity"] > 0
    assert payload["data"]["audit_event"]["details"]["advisory_only"] is True


def test_v1_forecast_batch_alias_runs_existing_read_only_batch_contract() -> None:
    response = _client().post(
        "/v1/forecast/batch",
        json={"actor": "program_a2_batch", "write_snapshots": False, "requests": [_request(on_hand=10), _request(on_hand=2)]},
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["resource"] == "forecast_batch"
    assert payload["advisory_only"] is True
    assert payload["read_only"] is True
    assert payload["inventory_source_of_truth_preserved"] is True
    assert payload["metadata"]["write_snapshots"] is False
    assert payload["data"]["count"] == 2
    assert len(payload["data"]["snapshots"]) == 2
