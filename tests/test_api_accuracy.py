import json
from pathlib import Path

from fastapi import HTTPException

from invyra_forecasting.api.accuracy_contracts import AccuracyEvaluationRequest
from invyra_forecasting.api.app import evaluate_accuracy, get_item_accuracy

ROOT = Path(__file__).resolve().parents[1]


def test_accuracy_evaluate_endpoint_runs_from_sample_payload():
    payload = AccuracyEvaluationRequest(**json.loads((ROOT / "data" / "sample" / "api" / "accuracy_evaluate_request.json").read_text(encoding="utf-8")))
    response = evaluate_accuracy(payload)
    assert response["accuracy"]["item_id"] == "ITEM-001"
    assert response["accuracy"]["forecast_quantity"] == 21
    assert response["accuracy"]["actual_quantity"] == 23
    assert response["accuracy"]["accuracy_rating"] in {"Low", "Medium", "High"}


def test_accuracy_evaluate_endpoint_rejects_mismatched_actuals():
    payload = AccuracyEvaluationRequest(**json.loads((ROOT / "data" / "sample" / "api" / "accuracy_evaluate_request.json").read_text(encoding="utf-8")))
    payload.actuals[0].item_id = "OTHER"
    try:
        evaluate_accuracy(payload)
    except HTTPException as exc:
        assert exc.status_code == 400
        assert "actual item_id mismatch" in str(exc.detail)
    else:  # pragma: no cover
        raise AssertionError("Expected HTTPException")


def test_get_item_accuracy_reads_persisted_records(tmp_path, monkeypatch):
    monkeypatch.setenv("INVYRA_ACCURACY_LOG_PATH", str(tmp_path / "accuracy_events.jsonl"))
    payload = AccuracyEvaluationRequest(**json.loads((ROOT / "data" / "sample" / "api" / "accuracy_evaluate_request.json").read_text(encoding="utf-8")))
    payload.persist = True
    evaluate_accuracy(payload)

    response = get_item_accuracy("ITEM-001", environment="TRAINING", limit=10)

    assert response["count"] == 1
    assert response["results"][0]["item_id"] == "ITEM-001"
    assert response["results"][0]["environment"] == "TRAINING"
