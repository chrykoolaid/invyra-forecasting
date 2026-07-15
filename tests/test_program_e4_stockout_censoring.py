from __future__ import annotations

import pytest

from invyra_forecasting.actual_outcome import ActualOutcomeEvidence
from invyra_forecasting.stockout_censoring import (
    StockoutCensoringService,
    StockoutCensoringStatus,
)


def _outcome(*, completeness: float = 1.0) -> ActualOutcomeEvidence:
    return ActualOutcomeEvidence(
        outcome_evidence_id="outcome-1",
        forecast_id="forecast-1",
        item_id="item-1",
        location_id="location-1",
        window_start_utc="2026-07-01T00:00:00+00:00",
        window_end_utc="2026-07-08T00:00:00+00:00",
        observed_quantity=8.0,
        outcome_source="inventory_ledger_export",
        evidence_refs=("ledger-1",),
        data_completeness=completeness,
    )


def test_uncensored_complete_outcome_is_ranking_eligible() -> None:
    assessment = StockoutCensoringService().classify(_outcome(), stockout_coverage=0.0)

    assert assessment.status is StockoutCensoringStatus.UNCENSORED
    assert assessment.ranking_evidence_eligible is True
    assert assessment.observed_quantity_unchanged == 8.0


def test_uncensored_incomplete_outcome_is_not_ranking_eligible() -> None:
    assessment = StockoutCensoringService().classify(
        _outcome(completeness=0.8), stockout_coverage=0.0
    )

    assert assessment.status is StockoutCensoringStatus.UNCENSORED
    assert assessment.ranking_evidence_eligible is False
    assert "incomplete" in assessment.warnings[0]


def test_partial_stockout_is_classified_without_adjusting_quantity() -> None:
    assessment = StockoutCensoringService().classify(
        _outcome(),
        stockout_coverage=0.4,
        stockout_evidence_refs=("availability-log-1",),
    )

    assert assessment.status is StockoutCensoringStatus.PARTIALLY_CENSORED
    assert assessment.ranking_evidence_eligible is False
    assert assessment.observed_quantity_unchanged == 8.0
    assert assessment.stockout_evidence_refs == ("availability-log-1",)


def test_full_stockout_is_classified_and_excluded() -> None:
    assessment = StockoutCensoringService().classify(
        _outcome(),
        stockout_coverage=1.0,
        stockout_evidence_refs=("availability-log-1",),
    )

    assert assessment.status is StockoutCensoringStatus.FULLY_CENSORED
    assert assessment.ranking_evidence_eligible is False


def test_missing_stockout_coverage_is_insufficient_evidence() -> None:
    assessment = StockoutCensoringService().classify(_outcome(), stockout_coverage=None)

    assert assessment.status is StockoutCensoringStatus.INSUFFICIENT_EVIDENCE
    assert assessment.ranking_evidence_eligible is False


def test_positive_stockout_coverage_requires_traceable_evidence() -> None:
    with pytest.raises(ValueError, match="stockout evidence references"):
        StockoutCensoringService().classify(_outcome(), stockout_coverage=0.2)


def test_rejects_invalid_coverage_and_preserves_guardrails() -> None:
    with pytest.raises(ValueError, match="between 0.0 and 1.0"):
        StockoutCensoringService().classify(_outcome(), stockout_coverage=1.1)

    payload = StockoutCensoringService().classify(
        _outcome(), stockout_coverage=0.0
    ).to_dict()
    assert payload["status"] == "uncensored"
    assert payload["observed_quantity_unchanged"] == 8.0
    assert payload["advisory_only"] is True
    assert payload["read_only"] is True
    assert payload["inventory_source_of_truth_preserved"] is True
