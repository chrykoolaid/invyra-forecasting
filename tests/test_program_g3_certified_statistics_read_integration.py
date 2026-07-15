from __future__ import annotations

import json
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient

from invyra_forecasting.api import tenant_context
from invyra_forecasting.api.app import app
from invyra_forecasting.certified_statistics_persistence import (
    CertifiedModelPerformanceStatisticsRecord,
    JsonlCertifiedStatisticsRepository,
)
from invyra_forecasting.model_performance_statistics import ModelPerformanceStatistics


@contextmanager
def _tenant(tenant_id: str):
    token = tenant_context._TENANT_ID.set(tenant_context.normalize_tenant_id(tenant_id))
    try:
        yield
    finally:
        tenant_context._TENANT_ID.reset(token)


def _statistics(*, count: int, accuracy: float | None, horizon: int = 7):
    return ModelPerformanceStatistics(
        registry_id="registry-1",
        model_name="seasonal-naive",
        model_version="1.0",
        forecast_horizon_days=horizon,
        eligible_evaluation_count=count,
        mae=None if count == 0 else 2.0,
        rmse=None if count == 0 else 2.5,
        mape=None if count == 0 else 0.2,
        bias=None if count == 0 else 0.1,
        average_accuracy_score=accuracy,
        average_calibration_gap=None if count == 0 else 0.05,
    )


def _record(*, record_id: str, namespace: str, count: int, accuracy: float, certified_at: str):
    return CertifiedModelPerformanceStatisticsRecord(
        record_id=record_id,
        namespace=namespace,
        statistics=_statistics(count=count, accuracy=accuracy),
        evidence_refs=(f"evaluation-{record_id}",),
        certified_at_utc=certified_at,
    )


def _registry_record(namespace: str) -> dict:
    return {
        "registry_id": "registry-1",
        "model_name": "seasonal-naive",
        "model_version": "1.0",
        "lifecycle_status": "active",
        "supported_forecast_horizons": [7, 14],
        "supported_demand_profiles": ["seasonal"],
        "namespace": namespace,
        "registered_at_utc": "2026-07-16T00:00:00+00:00",
        "schema_version": "1.0.0",
        "advisory_only": True,
        "read_only": True,
        "inventory_source_of_truth_preserved": True,
    }


def test_jsonl_repository_reconstructs_latest_tenant_scoped_snapshot(tmp_path) -> None:
    path = tmp_path / "certified-statistics.jsonl"
    with _tenant("alpha"):
        repository = JsonlCertifiedStatisticsRepository(path)
        repository.append(
            _record(
                record_id="older",
                namespace="alpha",
                count=10,
                accuracy=0.7,
                certified_at="2026-07-15T00:00:00+00:00",
            )
        )
        repository.append(
            _record(
                record_id="newer",
                namespace="alpha",
                count=40,
                accuracy=0.9,
                certified_at="2026-07-16T00:00:00+00:00",
            )
        )

    with _tenant("bravo"):
        JsonlCertifiedStatisticsRepository(path).append(
            _record(
                record_id="bravo",
                namespace="bravo",
                count=100,
                accuracy=0.99,
                certified_at="2026-07-16T00:00:00+00:00",
            )
        )

    with _tenant("alpha"):
        latest = JsonlCertifiedStatisticsRepository(path).latest_by_identity()

    assert [record.record_id for record in latest] == ["newer"]
    assert latest[0].statistics.eligible_evaluation_count == 40
    assert latest[0].statistics.average_accuracy_score == 0.9


def test_record_requires_traceable_evidence_for_certified_evaluations() -> None:
    with pytest.raises(ValueError, match="require evidence references"):
        CertifiedModelPerformanceStatisticsRecord(
            record_id="bad",
            namespace="alpha",
            statistics=_statistics(count=10, accuracy=0.8),
            evidence_refs=(),
            certified_at_utc="2026-07-16T00:00:00+00:00",
        )


def test_enterprise_api_reads_latest_certified_statistics(monkeypatch, tmp_path) -> None:
    registry_path = tmp_path / "registry.jsonl"
    registry_path.write_text(json.dumps(_registry_record("alpha")) + "\n", encoding="utf-8")
    statistics_path = tmp_path / "statistics.jsonl"
    records = (
        _record(
            record_id="older",
            namespace="alpha",
            count=10,
            accuracy=0.7,
            certified_at="2026-07-15T00:00:00+00:00",
        ),
        _record(
            record_id="newer",
            namespace="alpha",
            count=40,
            accuracy=0.9,
            certified_at="2026-07-16T00:00:00+00:00",
        ),
        _record(
            record_id="other-tenant",
            namespace="bravo",
            count=100,
            accuracy=0.99,
            certified_at="2026-07-16T00:00:00+00:00",
        ),
    )
    statistics_path.write_text(
        "\n".join(json.dumps(record.to_dict()) for record in records) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("INVYRA_MODEL_PERFORMANCE_REGISTRY_PATH", str(registry_path))
    monkeypatch.setenv("INVYRA_CERTIFIED_STATISTICS_PATH", str(statistics_path))

    response = TestClient(app).get(
        "/v1/intelligence/enterprise/summary",
        headers={"X-Tenant-Id": "alpha", "X-Request-Id": "request-g3"},
        params={"as_of_utc": "2026-07-16T01:00:00+00:00"},
    )

    assert response.status_code == 200
    payload = response.json()
    data = payload["data"]
    assert data["model_version_count"] == 1
    assert data["evaluated_model_version_count"] == 1
    assert data["total_eligible_evaluation_count"] == 40
    assert data["weighted_average_accuracy_score"] == 0.9
    assert data["models"][0]["confidence_status"] == "trusted"
    assert data["models"][0]["evidence_refs"] == ["evaluation-newer"]
    assert payload["metadata"]["certified_statistics_available"] is True
    assert payload["metadata"]["request_id"] == "request-g3"


def test_api_rejects_statistics_that_do_not_match_registered_model(monkeypatch, tmp_path) -> None:
    registry_path = tmp_path / "registry.jsonl"
    registry_path.write_text(json.dumps(_registry_record("alpha")) + "\n", encoding="utf-8")
    statistics_path = tmp_path / "statistics.jsonl"
    record = _record(
        record_id="mismatch",
        namespace="alpha",
        count=40,
        accuracy=0.9,
        certified_at="2026-07-16T00:00:00+00:00",
    ).to_dict()
    record["statistics"]["model_version"] = "2.0"
    statistics_path.write_text(json.dumps(record) + "\n", encoding="utf-8")
    monkeypatch.setenv("INVYRA_MODEL_PERFORMANCE_REGISTRY_PATH", str(registry_path))
    monkeypatch.setenv("INVYRA_CERTIFIED_STATISTICS_PATH", str(statistics_path))

    response = TestClient(app).get(
        "/v1/intelligence/enterprise/summary",
        headers={"X-Tenant-Id": "alpha"},
    )

    assert response.status_code == 400
    assert "registered model identity" in response.json()["detail"]


def test_repository_exposes_append_only_surface() -> None:
    exposed = {
        name for name in dir(JsonlCertifiedStatisticsRepository) if not name.startswith("_")
    }
    assert "append" in exposed
    assert "all" in exposed
    assert "latest_by_identity" in exposed
    assert "update" not in exposed
    assert "delete" not in exposed
    assert "remove" not in exposed
