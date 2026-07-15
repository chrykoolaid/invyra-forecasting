from __future__ import annotations

import json

from fastapi.testclient import TestClient

from invyra_forecasting.api.app import app
from invyra_forecasting.model_performance_registry import ModelLifecycleStatus


def _registry_record(*, registry_id: str, namespace: str, model_name: str) -> dict:
    return {
        "registry_id": registry_id,
        "model_name": model_name,
        "model_version": "1.0",
        "lifecycle_status": ModelLifecycleStatus.ACTIVE.value,
        "supported_forecast_horizons": [7, 14],
        "supported_demand_profiles": ["stable"],
        "namespace": namespace,
        "registered_at_utc": "2026-07-16T00:00:00+00:00",
        "schema_version": "1.0.0",
        "advisory_only": True,
        "read_only": True,
        "inventory_source_of_truth_preserved": True,
    }


def _seed(monkeypatch, tmp_path) -> None:
    path = tmp_path / "model-performance-registry.jsonl"
    records = (
        _registry_record(registry_id="alpha-model", namespace="alpha", model_name="seasonal-naive"),
        _registry_record(registry_id="bravo-model", namespace="bravo", model_name="moving-average"),
    )
    path.write_text(
        "\n".join(json.dumps(record) for record in records) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("INVYRA_MODEL_PERFORMANCE_REGISTRY_PATH", str(path))


def test_exposes_tenant_scoped_registered_portfolio_summary(monkeypatch, tmp_path) -> None:
    _seed(monkeypatch, tmp_path)
    response = TestClient(app).get(
        "/v1/intelligence/enterprise/summary",
        params={"as_of_utc": "2026-07-16T01:00:00+00:00"},
        headers={"X-Tenant-Id": "alpha", "X-Request-Id": "request-g2-alpha"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["resource"] == "enterprise_forecast_intelligence_summary"
    assert payload["metadata"]["tenant_id"] == "alpha"
    assert payload["metadata"]["request_id"] == "request-g2-alpha"
    assert payload["data"]["namespace"] == "alpha"
    assert payload["data"]["as_of_utc"] == "2026-07-16T01:00:00+00:00"
    assert payload["data"]["model_version_count"] == 1
    assert payload["data"]["models"][0]["registry_id"] == "alpha-model"
    assert payload["data"]["models"][0]["confidence_status"] == "experimental"
    assert payload["data"]["total_eligible_evaluation_count"] == 0
    assert payload["metadata"]["certified_statistics_available"] is False


def test_preserves_tenant_isolation(monkeypatch, tmp_path) -> None:
    _seed(monkeypatch, tmp_path)
    client = TestClient(app)

    alpha = client.get(
        "/v1/intelligence/enterprise/summary",
        headers={"X-Tenant-Id": "alpha"},
    ).json()["data"]
    bravo = client.get(
        "/v1/intelligence/enterprise/summary",
        headers={"X-Tenant-Id": "bravo"},
    ).json()["data"]

    assert [item["registry_id"] for item in alpha["models"]] == ["alpha-model"]
    assert [item["registry_id"] for item in bravo["models"]] == ["bravo-model"]


def test_returns_honest_empty_summary_when_registry_is_absent(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv(
        "INVYRA_MODEL_PERFORMANCE_REGISTRY_PATH",
        str(tmp_path / "missing-registry.jsonl"),
    )
    response = TestClient(app).get(
        "/v1/intelligence/enterprise/summary",
        headers={"X-Tenant-Id": "empty-tenant"},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["model_version_count"] == 0
    assert data["models"] == []
    assert data["weighted_average_accuracy_score"] is None
    assert data["weighted_average_calibration_gap"] is None


def test_route_is_get_only_and_preserves_enterprise_guardrails(monkeypatch, tmp_path) -> None:
    _seed(monkeypatch, tmp_path)
    client = TestClient(app)
    response = client.get(
        "/v1/intelligence/enterprise/summary",
        headers={"X-Tenant-Id": "alpha"},
    )
    operations = client.get("/openapi.json").json()["paths"][
        "/v1/intelligence/enterprise/summary"
    ]

    assert response.status_code == 200
    assert set(operations) == {"get"}
    assert response.json()["advisory_only"] is True
    assert response.json()["read_only"] is True
    assert response.json()["inventory_source_of_truth_preserved"] is True
    assert "post" not in operations
    assert "put" not in operations
    assert "delete" not in operations


def test_invalid_as_of_timestamp_returns_validation_error(monkeypatch, tmp_path) -> None:
    _seed(monkeypatch, tmp_path)
    response = TestClient(app).get(
        "/v1/intelligence/enterprise/summary",
        params={"as_of_utc": "not-a-timestamp"},
        headers={"X-Tenant-Id": "alpha"},
    )

    assert response.status_code == 400
    assert "valid ISO-8601 timestamp" in response.json()["detail"]
