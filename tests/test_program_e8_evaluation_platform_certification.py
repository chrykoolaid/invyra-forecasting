from __future__ import annotations

import json
from contextlib import contextmanager

from fastapi.testclient import TestClient

from invyra_forecasting.api import tenant_context
from invyra_forecasting.api.app import app
from invyra_forecasting.evaluation_evidence_persistence import (
    EvaluationEvidenceRecord,
    EvaluationEvidenceStage,
    JsonlEvaluationEvidenceRepository,
)
from invyra_forecasting.ranking_evidence_eligibility import RankingEvidenceEligibilityPolicy


@contextmanager
def _tenant(tenant_id: str | None):
    token = tenant_context._TENANT_ID.set(tenant_context.normalize_tenant_id(tenant_id))
    try:
        yield
    finally:
        tenant_context._TENANT_ID.reset(token)


def _record(*, record_id: str, stage: EvaluationEvidenceStage, namespace: str, model_name: str = "seasonal-naive") -> EvaluationEvidenceRecord:
    final = stage is EvaluationEvidenceStage.FINAL
    return EvaluationEvidenceRecord(
        record_id=record_id,
        evaluation_id="evaluation-e8",
        history_id="history-e8",
        forecast_id="forecast-e8",
        outcome_evidence_id=f"outcome-{record_id}",
        stage=stage,
        linkage={"evaluation_id": "evaluation-e8", "history_id": "history-e8", "forecast_id": "forecast-e8", "item_id": "ITEM-E8", "location_id": "LOC-E8", "model_name": model_name, "model_version": "1.0", "forecast_horizon_days": 7, "advisory_only": True, "read_only": True, "inventory_source_of_truth_preserved": True},
        window_assessment={"final_evaluation_eligible": final, "advisory_only": True, "read_only": True, "inventory_source_of_truth_preserved": True},
        actual_outcome={"outcome_evidence_id": f"outcome-{record_id}", "forecast_id": "forecast-e8", "item_id": "ITEM-E8", "location_id": "LOC-E8", "data_completeness": 1.0 if final else 0.5, "evidence_refs": [f"ledger-{record_id}"], "observed_quantity": 42.0, "advisory_only": True, "read_only": True, "inventory_source_of_truth_preserved": True},
        censoring_assessment={"outcome_evidence_id": f"outcome-{record_id}", "forecast_id": "forecast-e8", "item_id": "ITEM-E8", "location_id": "LOC-E8", "status": "uncensored", "ranking_evidence_eligible": final, "observed_quantity_unchanged": 42.0, "advisory_only": True, "read_only": True, "inventory_source_of_truth_preserved": True},
        namespace=namespace,
        persisted_at_utc="2026-07-01T00:00:00+00:00" if not final else "2026-07-09T00:00:00+00:00",
    )


def test_e8_certifies_partial_to_final_durability_and_ranking_gate(tmp_path) -> None:
    path = tmp_path / "evaluation-evidence.jsonl"
    with _tenant("tenant-e8"):
        repository = JsonlEvaluationEvidenceRepository(path)
        repository.append(_record(record_id="partial-e8", stage=EvaluationEvidenceStage.PARTIAL, namespace="tenant-e8"))
        repository.append(_record(record_id="final-e8", stage=EvaluationEvidenceStage.FINAL, namespace="tenant-e8"))
        records = JsonlEvaluationEvidenceRepository(path).for_evaluation("evaluation-e8")
        decisions = tuple(RankingEvidenceEligibilityPolicy().assess(record) for record in records)

    assert [record.record_id for record in records] == ["partial-e8", "final-e8"]
    assert [decision.eligible for decision in decisions] == [False, True]
    assert decisions[0].exclusion_reasons
    assert decisions[1].exclusion_reasons == ()
    assert records[1].actual_outcome["observed_quantity"] == 42.0
    assert records[1].censoring_assessment["observed_quantity_unchanged"] == 42.0


def test_e8_certifies_tenant_isolation_after_restart_and_through_api(tmp_path, monkeypatch) -> None:
    path = tmp_path / "evaluation-evidence.jsonl"
    for tenant_id, model_name in (("alpha", "model-alpha"), ("bravo", "model-bravo")):
        with _tenant(tenant_id):
            JsonlEvaluationEvidenceRepository(path).append(_record(record_id="shared-record", stage=EvaluationEvidenceStage.FINAL, namespace=tenant_id, model_name=model_name))

    monkeypatch.setenv("INVYRA_EVALUATION_EVIDENCE_PATH", str(path))
    client = TestClient(app)
    alpha = client.get("/v1/evaluations/evaluation-e8", headers={"X-Tenant-Id": "alpha"})
    bravo = client.get("/v1/evaluations/evaluation-e8", headers={"X-Tenant-Id": "bravo"})

    assert alpha.status_code == 200
    assert bravo.status_code == 200
    assert alpha.json()["data"]["items"][0]["linkage"]["model_name"] == "model-alpha"
    assert bravo.json()["data"]["items"][0]["linkage"]["model_name"] == "model-bravo"
    assert alpha.json()["metadata"]["tenant_id"] == "alpha"
    assert bravo.json()["metadata"]["tenant_id"] == "bravo"


def test_e8_certifies_read_only_api_and_request_correlation(tmp_path, monkeypatch) -> None:
    path = tmp_path / "evaluation-evidence.jsonl"
    path.write_text(json.dumps(_record(record_id="final-api-e8", stage=EvaluationEvidenceStage.FINAL, namespace="tenant-e8").to_dict()) + "\n", encoding="utf-8")
    monkeypatch.setenv("INVYRA_EVALUATION_EVIDENCE_PATH", str(path))
    client = TestClient(app)
    response = client.get("/v1/evaluations?stage=final", headers={"X-Tenant-Id": "tenant-e8", "X-Request-Id": "request-e8-certified"})
    schema = client.get("/openapi.json").json()
    paths = {path: operations for path, operations in schema["paths"].items() if path.startswith("/v1/evaluations") or path == "/v1/models/{model_name}/performance"}

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "request-e8-certified"
    assert response.json()["metadata"]["request_id"] == "request-e8-certified"
    assert response.json()["advisory_only"] is True
    assert response.json()["read_only"] is True
    assert response.json()["inventory_source_of_truth_preserved"] is True
    assert paths and all(set(operations) == {"get"} for operations in paths.values())


def test_e8_certifies_policy_does_not_score_rank_or_weight_models() -> None:
    payload = RankingEvidenceEligibilityPolicy().assess(_record(record_id="final-policy-e8", stage=EvaluationEvidenceStage.FINAL, namespace="tenant-e8")).to_dict()

    assert payload["eligible"] is True
    assert "score" not in payload
    assert "rank" not in payload
    assert "weight" not in payload
    assert payload["advisory_only"] is True
    assert payload["read_only"] is True
    assert payload["inventory_source_of_truth_preserved"] is True
