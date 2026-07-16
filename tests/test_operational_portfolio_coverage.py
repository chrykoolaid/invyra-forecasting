from contextlib import contextmanager
from dataclasses import FrozenInstanceError

import pytest

from invyra_forecasting.api import tenant_context
from invyra_forecasting.history import ForecastHistoryRecord
from invyra_forecasting.operational_portfolio_breakdown import (
    OperationalForecastPortfolioBreakdownService,
)
from invyra_forecasting.operational_portfolio_coverage import (
    OperationalPortfolioCoveragePolicy,
    OperationalPortfolioCoverageStatus,
)
from invyra_forecasting.operational_portfolio_summary import (
    OperationalForecastPortfolioSummaryService,
)


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
    evidence: bool,
    snapshot: bool,
    item_id: str = "ITEM-1",
    location_id: str = "LOC-1",
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
        return OperationalPortfolioCoveragePolicy().classify(summary, breakdown)


def test_empty_portfolio_is_unavailable_without_invented_ratios() -> None:
    result = _assessment(())
    assert result.status is OperationalPortfolioCoverageStatus.UNAVAILABLE
    assert result.evidence_coverage_ratio is None
    assert result.snapshot_coverage_ratio is None
    assert result.forecast_record_count == 0
    assert result.reasons == (
        "No forecast-history records are available for the requested boundary.",
    )


@pytest.mark.parametrize(
    ("covered", "expected"),
    [
        (1, OperationalPortfolioCoverageStatus.LIMITED),
        (2, OperationalPortfolioCoverageStatus.DEVELOPING),
        (3, OperationalPortfolioCoverageStatus.ESTABLISHED),
        (4, OperationalPortfolioCoverageStatus.COMPLETE),
    ],
)
def test_fixed_coverage_thresholds_are_deterministic(covered, expected) -> None:
    records = tuple(
        _record(f"history-{index}", evidence=index <= covered, snapshot=index <= covered)
        for index in range(1, 5)
    )
    result = _assessment(records)
    assert result.status is expected
    assert result.evidence_coverage_ratio == covered / 4
    assert result.snapshot_coverage_ratio == covered / 4
    assert result.item_count == 1
    assert result.location_count == 1
    assert result.item_location_count == 1
    assert "does not classify stock or forecast risk" in result.reasons[-1]


def test_lower_linkage_dimension_controls_status() -> None:
    records = (
        _record("history-1", evidence=True, snapshot=True),
        _record("history-2", evidence=True, snapshot=False),
        _record("history-3", evidence=True, snapshot=False),
        _record("history-4", evidence=True, snapshot=False),
    )
    result = _assessment(records)
    assert result.status is OperationalPortfolioCoverageStatus.LIMITED
    assert result.evidence_coverage_ratio == 1.0
    assert result.snapshot_coverage_ratio == 0.25


def test_assessment_is_immutable_and_serialization_is_defensive() -> None:
    result = _assessment((_record("history-1", evidence=True, snapshot=True),))
    with pytest.raises(FrozenInstanceError):
        result.status = OperationalPortfolioCoverageStatus.LIMITED
    payload = result.to_dict()
    payload["reasons"].append("changed")
    payload["history_refs"].clear()
    assert len(result.reasons) == 3
    assert result.history_refs == ("history-1",)


def test_mismatched_tenant_inputs_are_rejected() -> None:
    records = (_record("history-1", evidence=True, snapshot=True),)
    with _tenant("tenant-a"):
        summary = OperationalForecastPortfolioSummaryService().summarize(
            records, as_of_utc="2026-07-31T00:00:00+00:00"
        )
    with _tenant("tenant-b"):
        breakdown = OperationalForecastPortfolioBreakdownService().breakdown(
            records, as_of_utc="2026-07-31T00:00:00+00:00"
        )
    with pytest.raises(ValueError, match="same tenant namespace"):
        OperationalPortfolioCoveragePolicy().classify(summary, breakdown)
