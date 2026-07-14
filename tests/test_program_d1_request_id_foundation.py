from __future__ import annotations

from uuid import UUID

from fastapi.testclient import TestClient

from invyra_forecasting.api.app import app
from invyra_forecasting.api.runtime import ALLOWED_HEADERS
from invyra_forecasting.api.tenant_context import current_request_id, normalize_request_id


def _client() -> TestClient:
    return TestClient(app)


def test_request_id_header_is_allowed_for_cors_requests() -> None:
    assert "X-Request-Id" in ALLOWED_HEADERS


def test_request_id_is_generated_and_returned_for_every_http_response() -> None:
    response = _client().get("/health")

    assert response.status_code == 200
    assert str(UUID(response.headers["x-request-id"])) == response.headers["x-request-id"]


def test_client_request_id_is_normalized_and_propagated_to_v1_metadata() -> None:
    response = _client().get(
        "/v1/observability/ping",
        headers={"X-Request-Id": "  request-local-001  ", "X-Tenant-Id": "tenant-a"},
    )

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "request-local-001"
    payload = response.json()
    assert payload["metadata"]["request_id"] == "request-local-001"
    assert payload["metadata"]["tenant_id"] == "tenant-a"
    assert payload["advisory_only"] is True
    assert payload["read_only"] is True
    assert payload["inventory_source_of_truth_preserved"] is True


def test_blank_request_id_is_replaced_with_generated_identifier() -> None:
    response = _client().get("/v1/models", headers={"X-Request-Id": "   "})

    request_id = response.headers["x-request-id"]
    assert str(UUID(request_id)) == request_id
    assert response.json()["metadata"]["request_id"] == request_id


def test_request_context_is_isolated_and_does_not_leak_between_requests() -> None:
    client = _client()

    first = client.get("/v1/models", headers={"X-Request-Id": "request-a"})
    second = client.get("/v1/models", headers={"X-Request-Id": "request-b"})
    generated = client.get("/v1/models")

    assert first.json()["metadata"]["request_id"] == "request-a"
    assert second.json()["metadata"]["request_id"] == "request-b"
    assert generated.json()["metadata"]["request_id"] not in {"request-a", "request-b"}
    assert current_request_id() is None


def test_request_id_normalization_is_non_destructive_and_blank_safe() -> None:
    assert normalize_request_id(None) is None
    assert normalize_request_id("   ") is None
    assert normalize_request_id("  request-c  ") == "request-c"
