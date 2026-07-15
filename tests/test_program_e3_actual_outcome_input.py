from __future__ import annotations

import pytest

from invyra_forecasting.actual_outcome import ActualOutcomeEvidenceService
from invyra_forecasting.evaluation_linkage import ForecastEvaluationLink
from invyra_forecasting.evaluation_window import EvaluationWindowAssessment, EvaluationWindowStatus


def _link() -> ForecastEvaluationLink:
    return ForecastEvaluationLink(
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


def _assessment(completeness: float = 1.0) -> EvaluationWindowAssessment:
    return EvaluationWindowAssessment(
        history_id="history-1",
        evaluation_id="evaluation-1",
        forecast_id="forecast-1",
        forecast_origin_utc="2026-07-01T00:00:00+00:00",
        forecast_horizon_end_utc="2026-07-08T00:00:00+00:00",
        assessed_at_utc="2026-07-09T00:00:00+00:00",
        actual_data_completeness=completeness,
        status=(
            EvaluationWindowStatus.FULLY_EVALUABLE
            if completeness == 1.0
            else EvaluationWindowStatus.INSUFFICIENT_ACTUAL_DATA
        ),
        final_evaluation_eligible=completeness == 1.0,
    )


def test_normalizes_actual_outcome_evidence_without_inference() -> None:
    evidence = ActualOutcomeEvidenceService().normalize(
        _link(),
        _assessment(),
        outcome_evidence_id="outcome-1",
        window_start_utc="2026-07-01T08:00:00+08:00",
        window_end_utc="2026-07-08T08:00:00+08:00",
        observed_quantity=42.0,
        outcome_source="inventory_ledger_export",
        evidence_refs=("ledger-export-1", "movement-summary-1"),
        data_completeness=1.0,
        notes=("Observed quantity supplied by Inventory",),
    )

    assert evidence.forecast_id == "forecast-1"
    assert evidence.item_id == "item-1"
    assert evidence.location_id == "location-1"
    assert evidence.observed_quantity == 42.0
    assert evidence.window_start_utc == "2026-07-01T00:00:00+00:00"
    assert evidence.window_end_utc == "2026-07-08T00:00:00+00:00"
    assert evidence.evidence_refs == ("ledger-export-1", "movement-summary-1")


def test_requires_traceable_evidence_and_non_negative_quantity() -> None:
    service = ActualOutcomeEvidenceService()
    kwargs = dict(
        outcome_evidence_id="outcome-1",
        window_start_utc="2026-07-01T00:00:00+00:00",
        window_end_utc="2026-07-08T00:00:00+00:00",
        outcome_source="inventory_ledger_export",
        data_completeness=1.0,
    )
    with pytest.raises(ValueError, match="evidence reference"):
        service.normalize(_link(), _assessment(), observed_quantity=1.0, evidence_refs=(), **kwargs)
    with pytest.raises(ValueError, match="must not be negative"):
        service.normalize(
            _link(), _assessment(), observed_quantity=-1.0, evidence_refs=("ledger-1",), **kwargs
        )


def test_requires_valid_timezone_aware_window() -> None:
    service = ActualOutcomeEvidenceService()
    with pytest.raises(ValueError, match="UTC offset"):
        service.normalize(
            _link(),
            _assessment(),
            outcome_evidence_id="outcome-1",
            window_start_utc="2026-07-01T00:00:00",
            window_end_utc="2026-07-08T00:00:00+00:00",
            observed_quantity=1.0,
            outcome_source="ledger",
            evidence_refs=("ledger-1",),
            data_completeness=1.0,
        )
    with pytest.raises(ValueError, match="must be after"):
        service.normalize(
            _link(),
            _assessment(),
            outcome_evidence_id="outcome-1",
            window_start_utc="2026-07-08T00:00:00+00:00",
            window_end_utc="2026-07-01T00:00:00+00:00",
            observed_quantity=1.0,
            outcome_source="ledger",
            evidence_refs=("ledger-1",),
            data_completeness=1.0,
        )


def test_completeness_must_match_window_assessment() -> None:
    with pytest.raises(ValueError, match="completeness must match"):
        ActualOutcomeEvidenceService().normalize(
            _link(),
            _assessment(0.8),
            outcome_evidence_id="outcome-1",
            window_start_utc="2026-07-01T00:00:00+00:00",
            window_end_utc="2026-07-08T00:00:00+00:00",
            observed_quantity=10.0,
            outcome_source="ledger",
            evidence_refs=("ledger-1",),
            data_completeness=1.0,
        )


def test_rejects_mismatched_identity_and_preserves_guardrails() -> None:
    mismatched = EvaluationWindowAssessment(
        **{**_assessment().to_dict(), "forecast_id": "other-forecast", "status": EvaluationWindowStatus.FULLY_EVALUABLE}
    )
    with pytest.raises(ValueError, match="forecast_id must match"):
        ActualOutcomeEvidenceService().normalize(
            _link(),
            mismatched,
            outcome_evidence_id="outcome-1",
            window_start_utc="2026-07-01T00:00:00+00:00",
            window_end_utc="2026-07-08T00:00:00+00:00",
            observed_quantity=10.0,
            outcome_source="ledger",
            evidence_refs=("ledger-1",),
            data_completeness=1.0,
        )

    payload = ActualOutcomeEvidenceService().normalize(
        _link(),
        _assessment(),
        outcome_evidence_id="outcome-1",
        window_start_utc="2026-07-01T00:00:00+00:00",
        window_end_utc="2026-07-08T00:00:00+00:00",
        observed_quantity=10.0,
        outcome_source="ledger",
        evidence_refs=("ledger-1",),
        data_completeness=1.0,
    ).to_dict()
    assert payload["advisory_only"] is True
    assert payload["read_only"] is True
    assert payload["inventory_source_of_truth_preserved"] is True
