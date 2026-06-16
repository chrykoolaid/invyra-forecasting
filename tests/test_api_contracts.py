from datetime import date, timedelta

from fastapi import HTTPException

from invyra_forecasting.api.app import audit_override, forecast_batch, forecast_item, health, reorder_recommendation, stockout_risk
from invyra_forecasting.api.contracts import BatchForecastRequest, ForecastRequest, ItemPayload, LocationPayload, OverrideAuditRequest, StockMovementPayload, StockPositionPayload, SupplierProfilePayload
from invyra_forecasting.constants import Environment, MovementType


def _request(on_hand: float = 10, environment: Environment = Environment.TRAINING) -> ForecastRequest:
    start = date(2026, 5, 18)
    movements = [
        StockMovementPayload(
            movement_id=f"MOV-{idx}",
            item_id="ITEM-001",
            location_id="LOC-001",
            movement_date=start + timedelta(days=idx),
            movement_type=MovementType.POS_SALE,
            quantity=2 if idx < 15 else 3,
            environment=environment,
        )
        for idx in range(30)
    ]
    return ForecastRequest(
        actor="api_test",
        environment=environment,
        anchor_date=date(2026, 6, 16),
        item=ItemPayload(item_id="ITEM-001", sku="SKU-1", name="Coffee", category="Grocery", minimum_order_quantity=6),
        location=LocationPayload(location_id="LOC-001", name="Training Store"),
        stock_position=StockPositionPayload(item_id="ITEM-001", location_id="LOC-001", on_hand=on_hand, environment=environment),
        movements=movements,
        supplier_profile=SupplierProfilePayload(supplier_id="SUP-001", item_id="ITEM-001", lead_time_days=5, lead_time_variability_days=1, minimum_order_quantity=6),
    )


def test_health_endpoint_contract():
    assert health()["status"] == "ok"
    assert health()["mode"] == "advisory"


def test_forecast_item_endpoint_runs_real_engine():
    response = forecast_item(_request(on_hand=10))
    assert response["forecast"]["forecast_quantity"] > 0
    assert response["recommendation"]["suggested_reorder_quantity"] % 6 == 0
    assert response["audit_event"]["event_type"] == "FORECAST_CREATED"
    assert response["audit_event"]["details"]["advisory_only"] is True


def test_batch_endpoint_returns_count_and_snapshots():
    response = forecast_batch(BatchForecastRequest(actor="batch_test", requests=[_request(on_hand=10), _request(on_hand=2)]))
    assert response["count"] == 2
    assert len(response["snapshots"]) == 2


def test_risk_and_recommendation_endpoints_return_focused_payloads():
    risk_response = stockout_risk(_request(on_hand=2))
    reorder_response = reorder_recommendation(_request(on_hand=2))
    assert risk_response["risk"]["stockout_risk"] in {"Low", "Medium", "High"}
    assert reorder_response["recommendation"]["reorder_needed"] is True
    assert reorder_response["explanation"]["summary"]


def test_environment_mismatch_returns_400_http_exception():
    request = _request(on_hand=10, environment=Environment.TRAINING)
    request.movements[0].environment = Environment.LIVE
    try:
        forecast_item(request)
    except HTTPException as exc:
        assert exc.status_code == 400
        assert "Environment mismatch" in str(exc.detail)
    else:  # pragma: no cover
        raise AssertionError("Expected HTTPException")


def test_override_audit_endpoint_creates_governed_event():
    response = audit_override(
        OverrideAuditRequest(
            actor="manager-1",
            environment=Environment.TRAINING,
            item_id="ITEM-001",
            location_id="LOC-001",
            original_recommendation={"suggested_reorder_quantity": 12},
            override_action="changed_quantity_to_18",
            reason="Supplier case pack changed.",
        )
    )
    assert response["audit_event"]["event_type"] == "FORECAST_RECOMMENDATION_OVERRIDDEN"
    assert response["audit_event"]["details"]["reason"] == "Supplier case pack changed."
