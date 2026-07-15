from __future__ import annotations

import pytest

from invyra_forecasting.actual_outcome import ActualOutcomeEvidence
from invyra_forecasting.api.tenant_context import _TENANT_ID
from invyra_forecasting.evaluation_evidence_persistence import (
    EvaluationEvidencePersistenceService,
    EvaluationEvidenceStage,
    JsonlEvaluationEvidenceRepository,
)
from invyra_forecasting.evaluation_linkage import ForecastEvaluationLink
from invyra_forecasting.evaluation_window import EvaluationWindowAssessment, EvaluationWindowStatus
from invyra_forecasting.stockout_censoring import StockoutCensoringAssessment, StockoutCensoringStatus


def _contracts(*, eligible: bool = True):
    link = ForecastEvaluationLink(
        link_id="link-1",
        evaluation_id="evaluation-1",
        history_id="history-1",
        forecast_id="forecast-1",
        snapshot_id="snapshot-1",
        item_id="item-1",
        location_id="location-1",
        model_name="baseline",
        model_version="1.0",
        forecast_horizon_days=7,
        history_version_number=1,
    )
    window = EvaluationWindowAssessment(
        history_id="history-1",
        evaluation_id="evaluation-1",
        forecast_id="forecast-1",
        forecast_origin_utc="2026-07-01T00:00:00+00:00",
        forecast_horizon_end_utc="2026-07-08T00:00:00+00:00",
        assessed_at_utc="2026-07-09T00:00:00+00:00",
        actual_data_completeness=1.0 if eligible else 0.5,
        status=(EvaluationWindowStatus.FULLY_EVALUABLE if eligible else EvaluationWindowStatus.INSUFFICIENT_ACTUAL_DATA),
        final_evaluation_eligible=eligible,
    )
    outcome = ActualOutcomeEvidence(
        outcome_evidence_id="outcome-1",
        forecast_id="forecast-1",
        item_id="item-1",
        location_id="location-1",
        window_start_utc="2026-07-01T00:00:00+00:00",
        window_end_utc="2026-07-08T00:00:00+00:00",
        observed_quantity=42.0,
        outcome_source="inventory_ledger_export",
        evidence_refs=("ledger-1",),
        data_completeness=1.0 if eligible else 0.5,
    )
    censoring = StockoutCensoringAssessment(
        outcome_evidence_id="outcome-1",
        forecast_id="forecast-1",
        item_id="item-1",
        location_id="location-1",
        status=StockoutCensoringStatus.UNCENSORED,
        stockout_coverage=0.0,
        stockout_evidence_refs=(),
        observed_quantity_unchanged=42.0,
        ranking_evidence_eligible=eligible,
    )
    return link, window, outcome, censoring


def test_persists_partial_then_final_append_only(tmp_path) -> None:
    repository = JsonlEvaluationEvidenceRepository(tmp_path / "evidence.jsonl")
    service = EvaluationEvidencePersistenceService(repository)
    link, window, outcome, censoring = _contracts()

    partial = service.persist(link, window, outcome, censoring, stage=EvaluationEvidenceStage.PARTIAL, record_id="partial-1")
    final = service.persist(link, window, outcome, censoring, stage=EvaluationEvidenceStage.FINAL, record_id="final-1")

    assert partial.stage is EvaluationEvidenceStage.PARTIAL
    assert final.stage is EvaluationEvidenceStage.FINAL
    assert [record.record_id for record in service.for_evaluation("evaluation-1")] == ["partial-1", "final-1"]


def test_reconstructs_after_restart_and_blocks_duplicate_final(tmp_path) -> None:
    path = tmp_path / "evidence.jsonl"
    link, window, outcome, censoring = _contracts()
    EvaluationEvidencePersistenceService(JsonlEvaluationEvidenceRepository(path)).persist(
        link, window, outcome, censoring, stage=EvaluationEvidenceStage.FINAL, record_id="final-1"
    )

    restarted = EvaluationEvidencePersistenceService(JsonlEvaluationEvidenceRepository(path))
    assert restarted.for_evaluation("evaluation-1")[0].actual_outcome["observed_quantity"] == 42.0
    with pytest.raises(ValueError, match="final evaluation evidence already persisted"):
        restarted.persist(link, window, outcome, censoring, stage=EvaluationEvidenceStage.FINAL, record_id="final-2")


def test_final_requires_complete_uncensored_eligibility(tmp_path) -> None:
    link, window, outcome, censoring = _contracts(eligible=False)
    service = EvaluationEvidencePersistenceService(JsonlEvaluationEvidenceRepository(tmp_path / "evidence.jsonl"))
    with pytest.raises(ValueError, match="final evidence requires"):
        service.persist(link, window, outcome, censoring, stage=EvaluationEvidenceStage.FINAL)
    partial = service.persist(link, window, outcome, censoring, stage=EvaluationEvidenceStage.PARTIAL)
    assert partial.stage is EvaluationEvidenceStage.PARTIAL


def test_tenant_namespaces_remain_isolated_after_restart(tmp_path) -> None:
    path = tmp_path / "evidence.jsonl"
    link, window, outcome, censoring = _contracts()
    token_a = _TENANT_ID.set("tenant-a")
    try:
        EvaluationEvidencePersistenceService(JsonlEvaluationEvidenceRepository(path)).persist(
            link, window, outcome, censoring, stage=EvaluationEvidenceStage.FINAL, record_id="tenant-a-final"
        )
    finally:
        _TENANT_ID.reset(token_a)

    token_b = _TENANT_ID.set("tenant-b")
    try:
        service_b = EvaluationEvidencePersistenceService(JsonlEvaluationEvidenceRepository(path))
        assert service_b.for_evaluation("evaluation-1") == ()
        service_b.persist(link, window, outcome, censoring, stage=EvaluationEvidenceStage.FINAL, record_id="tenant-b-final")
    finally:
        _TENANT_ID.reset(token_b)

    token_a = _TENANT_ID.set("tenant-a")
    try:
        records = EvaluationEvidencePersistenceService(JsonlEvaluationEvidenceRepository(path)).for_evaluation("evaluation-1")
        assert [record.record_id for record in records] == ["tenant-a-final"]
    finally:
        _TENANT_ID.reset(token_a)


def test_rejects_identity_mismatch_and_preserves_guardrails(tmp_path) -> None:
    link, window, outcome, censoring = _contracts()
    bad_outcome = ActualOutcomeEvidence(**{**outcome.to_dict(), "forecast_id": "other-forecast", "evidence_refs": tuple(outcome.evidence_refs), "notes": tuple(outcome.notes)})
    service = EvaluationEvidencePersistenceService(JsonlEvaluationEvidenceRepository(tmp_path / "evidence.jsonl"))
    with pytest.raises(ValueError, match="actual outcome identities must match"):
        service.persist(link, window, bad_outcome, censoring, stage=EvaluationEvidenceStage.PARTIAL)

    record = service.persist(link, window, outcome, censoring, stage=EvaluationEvidenceStage.FINAL)
    assert record.advisory_only is True
    assert record.read_only is True
    assert record.inventory_source_of_truth_preserved is True
