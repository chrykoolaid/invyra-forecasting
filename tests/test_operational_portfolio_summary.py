from contextlib import contextmanager
from dataclasses import FrozenInstanceError

import pytest

from invyra_forecasting.api import tenant_context
from invyra_forecasting.history import ForecastHistoryRecord
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
    created_at_utc: str,
    model_name: str = "seasonal-naive",
    model_version: str = "1.0",
    evidence_refs: tuple[str, ...] = (),
    snapshot_id: str | None = None,
) -> ForecastHistoryRecord:
    return ForecastHistoryRecord(
        history_id=history_id,
        forecast_id=f"forecast-{history_id}",
        item_id=item_id,
        location_id=location_id,
        model_name=model_name,
        model_version=model_version,
        forecast_payload={"forecast_quantity": 10.0},
        created_at_utc=created_at_utc,
        evidence_refs=evidence_refs,
        snapshot_id=snapshot_id,
    )


def test_summarizes_operational_history_without_recalculating_forecasts() -> None:
    records = (
        _record(
            "history-1",
            item_id="ITEM-1",
            location_id="LOC-1",
            created_at_utc="2026-07-01T00:00:00+00:00",
            evidence_refs=("eval-1",),
            snapshot_id="snapshot-1",
        ),
        _record(
            "history-2",
            item_id="ITEM-1",
            location_id="LOC-2",
            created_at_utc="2026-07-02T00:00:00+00:00",
            model_name="moving-average",
            evidence_refs=("eval-2",),
        ),
        _record(
            "history-3",
            item_id="ITEM-2",
            location_id="LOC-2",
            created_at_utc="2026-07-20T00:00:00+00:00",
        ),
    )
    with _tenant("tenant-a"):
        summary = OperationalForecastPortfolioSummaryService().summarize(
            records,
            as_of_utc="2026-07-10T00:00:00+00:00",
        )

    assert summary.namespace == "tenant-a"
    assert summary.forecast_record_count == 2
    assert summary.unique_item_count == 1
    assert summary.unique_location_count == 2
    assert summary.unique_item_location_count == 2
    assert summary.evidence_linked_record_count == 2
    assert summary.snapshot_linked_record_count == 1
    assert summary.model_usage_distribution == (
        ("moving-average:1.0", 1),
        ("seasonal-naive:1.0", 1),
    )
    assert summary.to_dict()["model_usage_distribution"] == {
        "moving-average:1.0": 1,
        "seasonal-naive:1.0": 1,
    }
    assert summary.history_refs == ("history-1", "history-2")
    assert summary.evidence_refs == ("eval-1", "eval-2")
    assert summary.advisory_only is True
    assert summary.read_only is True


def test_empty_history_produces_honest_zero_summary() -> None:
    with _tenant("tenant-a"):
        summary = OperationalForecastPortfolioSummaryService().summarize(
            (), as_of_utc="2026-07-10T00:00:00+00:00"
        )
    assert summary.forecast_record_count == 0
    assert summary.unique_item_count == 0
    assert summary.model_usage_distribution == ()
    assert summary.to_dict()["model_usage_distribution"] == {}
    assert summary.history_refs == ()
    assert summary.evidence_refs == ()


def test_summary_contract_is_deeply_immutable_and_requires_offset_timestamp() -> None:
    with _tenant("tenant-a"):
        summary = OperationalForecastPortfolioSummaryService().summarize(
            (), as_of_utc="2026-07-10T00:00:00+00:00"
        )
    with pytest.raises(FrozenInstanceError):
        summary.forecast_record_count = 1
    assert isinstance(summary.model_usage_distribution, tuple)
    with pytest.raises(ValueError, match="UTC offset"):
        OperationalForecastPortfolioSummaryService().summarize(
            (), as_of_utc="2026-07-10T00:00:00"
        )
