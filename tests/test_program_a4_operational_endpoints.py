from __future__ import annotations

from datetime import datetime

from fastapi.testclient import TestClient

from invyra_forecasting.api.app import app


def _client() -> TestClient:
    return TestClient(app)


def test_v1_metadata_includes_operational_endpoints() -> None:
    payload = _client().get("/v1").json()

    assert "/v1/metrics" in payload["data"]["stable_resources"]
    assert "/v1/observability/ping" in payload["data"]["stable_resources"]
    assert payload["advisory_only"] is True
    assert payload["read_only"] is True
    assert payload["inventory_source_of_truth_preserved"] is True


def test_metrics_returns_existing_monitoring_and_performance_summaries() -> None:
    response = _client().get("/v1/metrics")

    assert response.status_code == 200
    payload = response.json()

    assert payload["resource"] == "operational_metrics"
    assert payload["advisory_only"] is True
    assert payload["read_only"] is True
    assert payload["inventory_source_of_truth_preserved"] is True
    assert isinstance(payload["data"]["monitoring"], dict)
    assert isinstance(payload["data"]["performance"], dict)


def test_observability_ping_returns_read_only_liveness_contract() -> None:
    response = _client().get("/v1/observability/ping")

    assert response.status_code == 200
    payload = response.json()
    data = payload["data"]

    assert payload["resource"] == "observability_ping"
    assert payload["advisory_only"] is True
    assert payload["read_only"] is True
    assert payload["inventory_source_of_truth_preserved"] is True
    assert data["status"] == "ok"
    assert data["engine"] == "invyra-forecasting"
    assert data["engine_version"]
    assert data["timestamp_utc"].endswith("Z")
    datetime.fromisoformat(data["timestamp_utc"].replace("Z", "+00:00"))
