from __future__ import annotations

import json

from fastapi.testclient import TestClient

from invyra_forecasting.api.app import app


def _record(*, record_id: str, stage: str, namespace: str = "tenant-a") -> dict:
    return {
        "record_id": record_id,
        "evaluation_id": "evaluation-1",
        "history_id": "history-1",
        "forecast_id": "forecast-1",
        "outcome_evidence_id": f"outcome-{record_id}",
        "stage": stage,
        "linkage": {
            "evaluation_id": "evaluation-1",
            "history_id": "history-1",
            "forecast_id": "forecast-1",
            "item_id": "item-1",
            "location_id": "location-1",
            "model_name": "baseline",
            "model_version": "1.0",
        },
        "window_assessment": {"final_evaluation_eligible": stage == "final"},
        "actual_outcome": {"data_completeness": 1.0},
        "censoring_assessment": {
            "status": "uncensored",
            "ranking_evidence_eligible": stage == "final",
        },
        "namespace": namespace,
        "persisted_at_utc": f"2026-07-0{1 if stage == 'partial' else 2}T00:00:00+00:00",
        "advisory_only": True,
        "read_only": True,
        "inventory_source_of_truth_preserved": True,
    }


def _seed(monkeypatch, tmp_path) -> None:
    path = tmp_path / "evaluation-evidence.jsonl"
    records = [
        _record(record_id="record-partial", stage="partial"),
        _record(record_id="record-final", stage="final"),
        _record(record_id="record-other", stage="final", namespace="tenant-b"),
    ]
    path.write_text("\n".join(json.dumps(record) for record in records) + "\n", encoding="utf-8")
    monkeypatch.setenv("INVYRA_EVALUATION_EVIDENCE_PATH", str(path))


def test_lists_and_filters_tenant_scoped_evaluation_evidence(monkeypatch, tmp_path) -> None:
    _seed(monkeypatch, tmp_path)
    response = TestClient(app).get(
        "/v1/evaluations?stage=final&model_name=baseline",
        headers={"X-Tenant-Id": "tenant-a", "X-Request-Id": "request-e6-list"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["resource"] == "evaluation_evidence"
    assert payload["data"]["total"] == 1
    assert payload["data"]["items"][0]["record_id"] == "record-final"
    assert payload["metadata"]["tenant_id"] == "tenant-a"
    assert payload["metadata"]["request_id"] == "request-e6-list"
    assert payload["read_only"] is True


def test_exposes_evaluation_and_history_timelines(monkeypatch, tmp_path) -> None:
    _seed(monkeypatch, tmp_path)
    client = TestClient(app)
    headers = {"X-Tenant-Id": "tenant-a"}

    evaluation = client.get("/v1/evaluations/evaluation-1", headers=headers)
    assert evaluation.status_code == 200
    assert evaluation.json()["data"]["total"] == 2

    history = client.get("/v1/history/history-1/evaluation", headers=headers)
    assert history.status_code == 200
    assert history.json()["data"]["history_id"] == "history-1"
    assert history.json()["data"]["total"] == 2


def test_model_performance_reports_evidence_counts_not_new_accuracy(monkeypatch, tmp_path) -> None:
    _seed(monkeypatch, tmp_path)
    response = TestClient(app).get(
        "/v1/models/baseline/performance?model_version=1.0",
        headers={"X-Tenant-Id": "tenant-a"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["evidence_record_count"] == 2
    assert data["partial_record_count"] == 1
    assert data["final_record_count"] == 1
    assert data["ranking_eligible_final_count"] == 1
    assert data["accuracy_metrics_calculated"] is False


def test_evaluation_routes_return_not_found_within_active_tenant(monkeypatch, tmp_path) -> None:
    _seed(monkeypatch, tmp_path)
    response = TestClient(app).get(
        "/v1/evaluations/evaluation-1",
        headers={"X-Tenant-Id": "tenant-c"},
    )
    assert response.status_code == 404


def test_v1_metadata_lists_e6_read_only_resources() -> None:
    response = TestClient(app).get("/v1")
    assert response.status_code == 200
    resources = response.json()["data"]["stable_resources"]
    assert "/v1/evaluations" in resources
    assert "/v1/evaluations/{evaluation_id}" in resources
    assert "/v1/history/{history_id}/evaluation" in resources
    assert "/v1/models/{model_name}/performance" in resources
