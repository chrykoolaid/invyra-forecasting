from __future__ import annotations

from fastapi.testclient import TestClient

from invyra_forecasting.api.app import app
from invyra_forecasting.api.runtime import ALLOWED_HEADERS
from invyra_forecasting.api.tenant_context import normalize_tenant_id


def _client() -> TestClient:
    return TestClient(app)


def test_tenant_header_is_allowed_for_cors_requests() -> None:
    assert "X-Tenant-Id" in ALLOWED_HEADERS


def test_tenant_id_is_optional_and_does_not_change_default_contract() -> None:
    response = _client().get("/v1/observability/ping")

    assert response.status_code == 200
    assert "x-tenant-id" not in response.headers
    assert "tenant_id" not in response.json()["metadata"]


def test_tenant_id_is_echoed_in_response_header_and_v1_metadata() -> None:
    response = _client().get(
        "/v1/observability/ping",
        headers={"X-Tenant-Id": "tenant-local-001"},
    )

    assert response.status_code == 200
    assert response.headers["x-tenant-id"] == "tenant-local-001"
    payload = response.json()
    assert payload["metadata"]["tenant_id"] == "tenant-local-001"
    assert payload["advisory_only"] is True
    assert payload["read_only"] is True
    assert payload["inventory_source_of_truth_preserved"] is True


def test_tenant_context_is_request_scoped_without_cross_request_leakage() -> None:
    client = _client()

    tenant_response = client.get("/v1/models", headers={"X-Tenant-Id": "tenant-a"})
    default_response = client.get("/v1/models")

    assert tenant_response.json()["metadata"]["tenant_id"] == "tenant-a"
    assert "tenant_id" not in default_response.json()["metadata"]
    assert "x-tenant-id" not in default_response.headers


def test_tenant_id_normalization_is_non_destructive_and_blank_safe() -> None:
    assert normalize_tenant_id(None) is None
    assert normalize_tenant_id("   ") is None
    assert normalize_tenant_id("  tenant-b  ") == "tenant-b"
