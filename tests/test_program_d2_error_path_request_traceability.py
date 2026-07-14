from __future__ import annotations

from uuid import UUID

from fastapi.testclient import TestClient

from invyra_forecasting.api.app import app


def _client() -> TestClient:
    return TestClient(app)


def test_supplied_request_id_is_preserved_on_not_found_response() -> None:
    response = _client().get(
        "/v1/snapshots/missing-d2-snapshot",
        headers={"X-Request-Id": "request-d2-not-found"},
    )

    assert response.status_code == 404
    assert response.headers["x-request-id"] == "request-d2-not-found"
    assert response.json()["detail"] == "Snapshot not found: missing-d2-snapshot"


def test_generated_request_id_is_returned_on_not_found_response() -> None:
    response = _client().get("/v1/snapshots/missing-d2-generated")

    assert response.status_code == 404
    UUID(response.headers["x-request-id"])


def test_supplied_request_id_is_preserved_on_validation_error_response() -> None:
    response = _client().post(
        "/v1/forecast",
        json={},
        headers={"X-Request-Id": "request-d2-validation"},
    )

    assert response.status_code == 422
    assert response.headers["x-request-id"] == "request-d2-validation"
    assert response.json()["detail"]


def test_request_and_tenant_headers_coexist_on_error_responses() -> None:
    response = _client().get(
        "/v1/snapshots/missing-d2-tenant",
        headers={
            "X-Request-Id": "request-d2-tenant",
            "X-Tenant-Id": "tenant-d2",
        },
    )

    assert response.status_code == 404
    assert response.headers["x-request-id"] == "request-d2-tenant"
    assert response.headers["x-tenant-id"] == "tenant-d2"


def test_error_request_ids_remain_isolated_across_requests() -> None:
    client = _client()

    first = client.get(
        "/v1/snapshots/missing-d2-first",
        headers={"X-Request-Id": "request-d2-first"},
    )
    second = client.get("/v1/snapshots/missing-d2-second")

    assert first.status_code == 404
    assert second.status_code == 404
    assert first.headers["x-request-id"] == "request-d2-first"
    assert second.headers["x-request-id"] != "request-d2-first"
    UUID(second.headers["x-request-id"])


def test_error_traceability_does_not_change_enterprise_boundaries() -> None:
    response = _client().get(
        "/v1/snapshots/missing-d2-guardrails",
        headers={"X-Request-Id": "request-d2-guardrails"},
    )

    assert response.status_code == 404
    assert response.headers["x-request-id"] == "request-d2-guardrails"
    assert "inventory" not in response.json()["detail"].lower()
    assert "purchase order" not in response.json()["detail"].lower()
