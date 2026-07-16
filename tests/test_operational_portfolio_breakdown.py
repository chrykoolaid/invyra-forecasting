from contextlib import contextmanager
from dataclasses import FrozenInstanceError

import pytest

from invyra_forecasting.api import tenant_context
from invyra_forecasting.history import ForecastHistoryRecord
from invyra_forecasting.operational_portfolio_breakdown import (
    OperationalForecastPortfolioBreakdownService,
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
    item_id: str,
    location_id: str,
    created_at_utc: str,
    evidence_refs: tuple[str, ...] = (),
    snapshot_id: str | None = None,
) -> ForecastHistoryRecord:
    return ForecastHistoryRecord(
        history_id=history_id,
        forecast_id=f"forecast-{history_id}",
        item_id=item_id,
        location_id=location_id,
        model_name="seasonal-naive",
        model_version="1.0",
        forecast_payload={"forecast_quantity": 10.0},
        created_at_utc=created_at_utc,
        evidence_refs=evidence_refs,
        snapshot_id=snapshot_id,
    )


def test_breaks_history_down_by_item_location_and_pair() -> None:
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
            evidence_refs=("eval-2",),
        ),
        _record(
            "history-3",
            item_id="ITEM-1",
            location_id="LOC-1",
            created_at_utc="2026-07-03T00:00:00+00:00",
            evidence_refs=("eval-1", "eval-3"),
        ),
        _record(
            "history-future",
            item_id="ITEM-2",
            location_id="LOC-2",
            created_at_utc="2026-07-20T00:00:00+00:00",
        ),
    )

    with _tenant("tenant-a"):
        breakdown = OperationalForecastPortfolioBreakdownService().breakdown(
            records,
            as_of_utc="2026-07-10T00:00:00+00:00",
        )

    assert breakdown.namespace == "tenant-a"
    assert len(breakdown.items) == 1
    assert breakdown.items[0].item_id == "ITEM-1"
    assert breakdown.items[0].forecast_record_count == 3
    assert breakdown.items[0].evidence_linked_record_count == 3
    assert breakdown.items[0].snapshot_linked_record_count == 1
    assert breakdown.items[0].earliest_forecast_at_utc == "2026-07-01T00:00:00+00:00"
    assert breakdown.items[0].latest_forecast_at_utc == "2026-07-03T00:00:00+00:00"
    assert breakdown.items[0].history_refs == ("history-1", "history-2", "history-3")
    assert breakdown.items[0].evidence_refs == ("eval-1", "eval-2", "eval-3")

    assert [entry.location_id for entry in breakdown.locations] == ["LOC-1", "LOC-2"]
    assert [entry.forecast_record_count for entry in breakdown.locations] == [2, 1]
    assert [(entry.item_id, entry.location_id) for entry in breakdown.item_locations] == [
        ("ITEM-1", "LOC-1"),
        ("ITEM-1", "LOC-2"),
    ]
    assert [entry.forecast_record_count for entry in breakdown.item_locations] == [2, 1]
    assert breakdown.advisory_only is True
    assert breakdown.read_only is True
    assert breakdown.inventory_source_of_truth_preserved is True


def test_empty_history_returns_empty_immutable_breakdown() -> None:
    with _tenant("tenant-a"):
        breakdown = OperationalForecastPortfolioBreakdownService().breakdown(
            (), as_of_utc="2026-07-10T00:00:00+00:00"
        )

    assert breakdown.items == ()
    assert breakdown.locations == ()
    assert breakdown.item_locations == ()
    with pytest.raises(FrozenInstanceError):
        breakdown.as_of_utc = "changed"


def test_serialization_returns_json_safe_copies() -> None:
    with _tenant("tenant-a"):
        breakdown = OperationalForecastPortfolioBreakdownService().breakdown(
            (
                _record(
                    "history-1",
                    item_id="ITEM-1",
                    location_id="LOC-1",
                    created_at_utc="2026-07-01T00:00:00+00:00",
                    evidence_refs=("eval-1",),
                ),
            ),
            as_of_utc="2026-07-10T00:00:00+00:00",
        )

    payload = breakdown.to_dict()
    payload["items"][0]["history_refs"].append("changed")
    assert breakdown.items[0].history_refs == ("history-1",)


def test_breakdown_requires_offset_timestamp() -> None:
    with pytest.raises(ValueError, match="UTC offset"):
        OperationalForecastPortfolioBreakdownService().breakdown(
            (), as_of_utc="2026-07-10T00:00:00"
        )
