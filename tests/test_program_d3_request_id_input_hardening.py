from __future__ import annotations

from uuid import UUID

from fastapi.testclient import TestClient

from invyra_forecasting.api.app import app
from invyra_forecasting.api.tenant_context import MAX_REQUEST_ID_LENGTH, normalize_request_id


def _client() -> TestClient:
    return TestClient(app)


def _assert_generated_request_id(value: str) -> None:
    assert str(UUID(value)) == value


def test_request_id_accepts_bounded_visible_ascii() -> None:
    request_id = "request-ABC_123.trace"

    assert normalize_request_id(request_id) == request_id
    assert normalize_request_id("x" * MAX_REQUEST_ID_LENGTH) == "x" * MAX_REQUEST_ID_LENGTH


def test_request_id_rejects_control_characters_and_non_ascii() -> None:
    assert normalize_request_id("request\nforged") is None
    assert normalize_request_id("request\tforged") is None
    assert normalize_request_id("request-💡") is None


def test_request_id_rejects_values_over_maximum_length() -> None:
    assert normalize_request_id("x" * (MAX_REQUEST_ID_LENGTH + 1)) is None


def test_invalid_request_id_is_replaced_with_generated_identifier() -> None:
    response = _client().get(
        "/v1/observability/ping",
        headers={"X-Request-Id": "request-💡"},
    )

    assert response.status_code == 200
    request_id = response.headers["x-request-id"]
    _assert_generated_request_id(request_id)
    assert response.json()["metadata"]["request_id"] == request_id


def test_oversized_request_id_is_replaced_without_affecting_tenant_context() -> None:
    response = _client().get(
        "/v1/models",
        headers={
            "X-Request-Id": "x" * (MAX_REQUEST_ID_LENGTH + 1),
            "X-Tenant-Id": "tenant-d3",
        },
    )

    assert response.status_code == 200
    request_id = response.headers["x-request-id"]
    _assert_generated_request_id(request_id)
    assert response.headers["x-tenant-id"] == "tenant-d3"
    assert response.json()["metadata"]["request_id"] == request_id
    assert response.json()["metadata"]["tenant_id"] == "tenant-d3"


def test_valid_client_request_id_contract_remains_compatible() -> None:
    response = _client().get(
        "/v1/observability/ping",
        headers={"X-Request-Id": "request-d3-valid"},
    )

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "request-d3-valid"
    assert response.json()["metadata"]["request_id"] == "request-d3-valid"
