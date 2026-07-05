from __future__ import annotations

import pytest

from invyra_forecasting.evaluation import (
    EvaluationPersistenceService,
    EvaluationQuery,
    ForecastEvaluationService,
    ForecastOutcome,
    ForecastPrediction,
)


def _evaluation_result(forecast_id: str = "forecast-1"):
    evaluator = ForecastEvaluationService()
    return evaluator.evaluate(
        ForecastPrediction(
            forecast_id=forecast_id,
            item_id="item-1",
            location_id="location-1",
            model_name="baseline_explainable_demand_model",
            model_version="2W.1",
            forecast_horizon_days=30,
            predicted_quantity=100.0,
            confidence=0.8,
        ),
        ForecastOutcome(
            forecast_id=forecast_id,
            actual_quantity=90.0,
            outcome_source="ledger_observed_outcome",
        ),
    )


def test_phase_6b_persists_and_retrieves_evaluation_record() -> None:
    service = EvaluationPersistenceService()
    result = _evaluation_result()

    record = service.persist(
        result,
        evaluation_id="evaluation-1",
        snapshot_id="snapshot-1",
        evidence_refs=("evidence-1",),
        audit_refs=("audit-1",),
    )

    fetched = service.get("evaluation-1")
    assert fetched == record
    assert fetched is not None
    assert fetched.forecast_id == "forecast-1"
    assert fetched.snapshot_id == "snapshot-1"
    assert fetched.evidence_refs == ("evidence-1",)
    assert fetched.audit_refs == ("audit-1",)
    assert fetched.advisory_only is True
    assert fetched.read_only is True


def test_phase_6b_rejects_duplicate_evaluation_ids() -> None:
    service = EvaluationPersistenceService()
    result = _evaluation_result()
    service.persist(result, evaluation_id="evaluation-1")

    with pytest.raises(ValueError, match="evaluation already persisted"):
        service.persist(result, evaluation_id="evaluation-1")


def test_phase_6b_queries_by_forecast_model_and_snapshot() -> None:
    service = EvaluationPersistenceService()
    first = _evaluation_result("forecast-1")
    second = _evaluation_result("forecast-2")
    service.persist(first, evaluation_id="evaluation-1", snapshot_id="snapshot-a")
    service.persist(second, evaluation_id="evaluation-2", snapshot_id="snapshot-b")

    forecast_records = service.query(EvaluationQuery(forecast_id="forecast-1"))
    snapshot_records = service.query(EvaluationQuery(snapshot_id="snapshot-b"))
    model_records = service.query(EvaluationQuery(model_name="baseline_explainable_demand_model", model_version="2W.1"))

    assert [record.evaluation_id for record in forecast_records] == ["evaluation-1"]
    assert [record.evaluation_id for record in snapshot_records] == ["evaluation-2"]
    assert [record.evaluation_id for record in model_records] == ["evaluation-1", "evaluation-2"]


def test_phase_6b_summarizes_persisted_evaluations_with_flags() -> None:
    service = EvaluationPersistenceService()
    service.persist(_evaluation_result("forecast-1"), evaluation_id="evaluation-1")
    service.persist(_evaluation_result("forecast-2"), evaluation_id="evaluation-2")

    summary = service.summarize()

    assert summary["count"] == 2
    assert summary["mae"] == 10.0
    assert summary["rmse"] == 10.0
    assert summary["mape"] == 0.1111
    assert summary["bias"] == -10.0
    assert summary["average_accuracy_score"] == 0.8889
    assert summary["advisory_only"] is True
    assert summary["read_only"] is True


def test_phase_6b_timeline_for_forecast_returns_matching_records() -> None:
    service = EvaluationPersistenceService()
    service.persist(_evaluation_result("forecast-1"), evaluation_id="evaluation-1")
    service.persist(_evaluation_result("forecast-2"), evaluation_id="evaluation-2")

    timeline = service.timeline_for_forecast("forecast-1")

    assert len(timeline) == 1
    assert timeline[0].evaluation_id == "evaluation-1"
