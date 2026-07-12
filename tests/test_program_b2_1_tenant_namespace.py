from __future__ import annotations

import asyncio
from datetime import date, timedelta

from fastapi.testclient import TestClient

from invyra_forecasting.api.app import app
from invyra_forecasting.api.contracts import (
    ForecastRequest,
    ItemPayload,
    LocationPayload,
    StockMovementPayload,
    StockPositionPayload,
    SupplierProfilePayload,
)
from invyra_forecasting.api.tenant_context import TenantContextMiddleware
from invyra_forecasting.api.tenant_namespace import (
    DEFAULT_NAMESPACE,
    current_namespace,
    normalize_namespace,
)
from invyra_forecasting.constants import Environment, MovementType


def _forecast_request() -> dict:
    start = date(2026, 5, 18)
    movements = [
        StockMovementPayload(
            movement_id=f"B21-MOV-{index}",
            item_id="B21-ITEM-001",
            location_id="B21-LOC-001",
            movement_date=start + timedelta(days=index),
            movement_type=MovementType.POS_SALE,
            quantity=2,
            environment=Environment.TRAINING,
        ).model_dump(mode="json")
        for index in range(30)
    ]
    return ForecastRequest(
        actor="program_b2_1_test",
        environment=Environment.TRAINING,
        anchor_date=date(2026, 6, 16),
        write_snapshot=False,
        item=ItemPayload(
            item_id="B21-ITEM-001",
            sku="B21-SKU-1",
            name="Coffee",
            category="Grocery",
            minimum_order_quantity=6,
        ),
        location=LocationPayload(location_id="B21-LOC-001", name="Training Store"),
        stock_position=StockPositionPayload(
            item_id="B21-ITEM-001",
            location_id="B21-LOC-001",
            on_hand=10,
            environment=Environment.TRAINING,
        ),
        movements=movements,
        supplier_profile=SupplierProfilePayload(
            supplier_id="B21-SUP-001",
            item_id="B21-ITEM-001",
            lead_time_days=5,
            lead_time_variability_days=1,
            minimum_order_quantity=6,
        ),
    ).model_dump(mode="json")


def test_namespace_normalization_uses_default_for_missing_or_blank_values() -> None:
    assert normalize_namespace(None) == DEFAULT_NAMESPACE
    assert normalize_namespace("") == DEFAULT_NAMESPACE
    assert normalize_namespace("   ") == DEFAULT_NAMESPACE


def test_namespace_normalization_trims_and_preserves_valid_tenant_ids() -> None:
    assert normalize_namespace(" alpha ") == "alpha"
    assert normalize_namespace("tenant-01") == "tenant-01"


def test_current_namespace_defaults_outside_a_tenant_request() -> None:
    assert current_namespace() == DEFAULT_NAMESPACE


async def _namespace_for_request(tenant_id: str | None) -> tuple[str, str]:
    observed_namespace = ""

    async def endpoint(scope, receive, send) -> None:
        nonlocal observed_namespace
        observed_namespace = current_namespace()
        await asyncio.sleep(0)
        assert current_namespace() == observed_namespace
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    headers = [] if tenant_id is None else [(b"x-tenant-id", tenant_id.encode("latin-1"))]
    scope = {"type": "http", "headers": headers}
    messages = iter([{"type": "http.request", "body": b"", "more_body": False}])

    async def receive():
        return next(messages)

    async def send(message) -> None:
        return None

    await TenantContextMiddleware(endpoint)(scope, receive, send)
    return observed_namespace, current_namespace()


def test_namespace_is_request_scoped_and_does_not_leak_between_concurrent_requests() -> None:
    async def run_requests() -> list[tuple[str, str]]:
        return await asyncio.gather(
            _namespace_for_request(" alpha "),
            _namespace_for_request("bravo"),
            _namespace_for_request(None),
        )

    results = asyncio.run(run_requests())

    assert results == [
        ("alpha", DEFAULT_NAMESPACE),
        ("bravo", DEFAULT_NAMESPACE),
        (DEFAULT_NAMESPACE, DEFAULT_NAMESPACE),
    ]


def test_forecast_outputs_are_identical_across_namespaces() -> None:
    client = TestClient(app)
    request = _forecast_request()

    alpha_response = client.post("/v1/forecast", json=request, headers={"X-Tenant-Id": "alpha"})
    bravo_response = client.post("/v1/forecast", json=request, headers={"X-Tenant-Id": "bravo"})

    assert alpha_response.status_code == 200
    assert bravo_response.status_code == 200

    alpha_payload = alpha_response.json()
    bravo_payload = bravo_response.json()

    assert alpha_payload["metadata"]["tenant_id"] == "alpha"
    assert bravo_payload["metadata"]["tenant_id"] == "bravo"

    assert alpha_payload["resource"] == bravo_payload["resource"]
    assert alpha_payload["advisory_only"] is True
    assert bravo_payload["advisory_only"] is True
    assert alpha_payload["read_only"] is True
    assert bravo_payload["read_only"] is True
    assert alpha_payload["inventory_source_of_truth_preserved"] is True
    assert bravo_payload["inventory_source_of_truth_preserved"] is True

    stable_output_fields = (
        "forecast",
        "confidence",
        "explanation",
        "recommendation",
        "risk",
        "input_summary",
        "intelligence_context",
    )
    for field in stable_output_fields:
        assert alpha_payload["data"][field] == bravo_payload["data"][field]
