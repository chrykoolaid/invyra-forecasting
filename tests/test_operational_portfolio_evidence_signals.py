from contextlib import contextmanager
from dataclasses import FrozenInstanceError

import pytest

from invyra_forecasting.api import tenant_context
from invyra_forecasting.history import ForecastHistoryRecord
from invyra_forecasting.operational_portfolio_breakdown import OperationalForecastPortfolioBreakdownService
from invyra_forecasting.operational_portfolio_coverage import OperationalPortfolioCoveragePolicy
from invyra_forecasting.operational_portfolio_evidence_signals import (
    OperationalEvidenceSignalSeverity,
    OperationalPortfolioEvidenceSignalPolicy,
)
from invyra_forecasting.operational_portfolio_summary import OperationalForecastPortfolioSummaryService


@contextmanager
def _tenant(tenant_id: str):
    token = tenant_context._TENANT_ID.set(tenant_context.normalize_tenant_id(tenant_id))
    try:
        yield
    finally:
        tenant_context._TENANT_ID.reset(token)


def _record(
    history_id: str,
    *,
    item_id: str,
    location_id: str,
    evidence: bool,
    snapshot: bool,
) -> ForecastHistoryRecord:
    return ForecastHistoryRecord(
        history_id=history_id,
        forecast_id=f"forecast-{history_id}",
        item_id=item_id,
        location_id=location_id,
        model_name="seasonal-naive",
        model_version="1.0",
        forecast_payload={"forecast_quantity": 10.0},
        created_at_utc=f"2026-07-{int(history_id.split('-')[-1]):02d}T00:00:00+00:00",
        evidence_refs=(f"eval-{history_id}",) if evidence else (),
        snapshot_id=f"snapshot-{history_id}" if snapshot else None,
    )


def _assessment(records: tuple[ForecastHistoryRecord, ...]):
    with _tenant("tenant-a"):
        summary = OperationalForecastPortfolioSummaryService().summarize(
            records, as_of_utc="2026-07-31T00:00:00+00:00"
        )
        breakdown = OperationalForecastPortfolioBreakdownService().breakdown(
            records, as_of_utc="2026-07-31T00:00:00+00:00"
        )
        coverage = OperationalPortfolioCoveragePolicy().classify(summary, breakdown)
        return OperationalPortfolioEvidenceSignalPolicy().assess(coverage, breakdown)


def test_empty_history_reports_one_informational_signal() -> None:
    result = _assessment(())
    assert [signal.code for signal in result.signals] == ["no_history"]
    assert result.signals[0].severity is OperationalEvidenceSignalSeverity.INFORMATIONAL
    assert result.signals[0].observed_value == 0


def test_complete_even_portfolio_returns_no_signals() -> None:
    records = (
        _record("history-1", item_id="ITEM-1", location_id="LOC-1", evidence=True, snapshot=True),
        _record("history-2", item_id="ITEM-2", location_id="LOC-2", evidence=True, snapshot=True),
    )
    result = _assessment(records)
    assert result.signals == ()


def test_missing_and_incomplete_linkage_are_reported_without_risk_inference() -> None:
    records = (
        _record("history-1", item_id="ITEM-1", location_id="LOC-1", evidence=False, snapshot=True),
        _record("history-2", item_id="ITEM-2", location_id="LOC-2", evidence=False, snapshot=False),
    )
    result = _assessment(records)
    assert [signal.code for signal in result.signals] == [
        "missing_evidence_linkage",
        "incomplete_snapshot_linkage",
    ]
    assert all(signal.severity is OperationalEvidenceSignalSeverity.WATCH for signal in result.signals)
    assert result.signals[0].observed_value == 0.0
    assert result.signals[1].observed_value == 0.5


def test_uneven_item_and_location_history_distributions_are_observed() -> None:
    records = (
        _record("history-1", item_id="ITEM-1", location_id="LOC-1", evidence=True, snapshot=True),
        _record("history-2", item_id="ITEM-1", location_id="LOC-1", evidence=True, snapshot=True),
        _record("history-3", item_id="ITEM-2", location_id="LOC-2", evidence=True, snapshot=True),
    )
    result = _assessment(records)
    assert [signal.code for signal in result.signals] == [
        "uneven_item_history_distribution",
        "uneven_location_history_distribution",
    ]
    assert all(signal.severity is OperationalEvidenceSignalSeverity.INFORMATIONAL for signal in result.signals)
    assert all(signal.observed_value == 2 for signal in result.signals)


def test_assessment_is_immutable_and_serialization_is_defensive() -> None:
    result = _assessment(())
    with pytest.raises(FrozenInstanceError):
        result.signals = ()
    payload = result.to_dict()
    payload["signals"][0]["history_refs"].append("changed")
    assert result.signals[0].history_refs == ()


def test_mismatched_tenant_inputs_are_rejected() -> None:
    records = (
        _record("history-1", item_id="ITEM-1", location_id="LOC-1", evidence=True, snapshot=True),
    )
    with _tenant("tenant-a"):
        summary = OperationalForecastPortfolioSummaryService().summarize(
            records, as_of_utc="2026-07-31T00:00:00+00:00"
        )
        breakdown_a = OperationalForecastPortfolioBreakdownService().breakdown(
            records, as_of_utc="2026-07-31T00:00:00+00:00"
        )
        coverage = OperationalPortfolioCoveragePolicy().classify(summary, breakdown_a)
    with _tenant("tenant-b"):
        breakdown_b = OperationalForecastPortfolioBreakdownService().breakdown(
            records, as_of_utc="2026-07-31T00:00:00+00:00"
        )
    with pytest.raises(ValueError, match="same tenant namespace"):
        OperationalPortfolioEvidenceSignalPolicy().assess(coverage, breakdown_b)
