from __future__ import annotations

from contextlib import contextmanager

import pytest

from invyra_forecasting.api import tenant_context
from invyra_forecasting.history import ForecastHistoryRecord
from invyra_forecasting.history_index import HistoricalSnapshotIndex, HistoryIndexQuery


@contextmanager
def _tenant(tenant_id: str | None):
    token = tenant_context._TENANT_ID.set(tenant_context.normalize_tenant_id(tenant_id))
    try:
        yield
    finally:
        tenant_context._TENANT_ID.reset(token)


def _record(
    history_id: str,
    *,
    forecast_id: str = "forecast-1",
    snapshot_id: str | None = "snapshot-1",
    version_number: int = 1,
    parent_history_id: str | None = None,
    created_at_utc: str = "2026-07-13T10:00:00+00:00",
) -> ForecastHistoryRecord:
    return ForecastHistoryRecord(
        history_id=history_id,
        forecast_id=forecast_id,
        item_id="ITEM-001",
        location_id="LOC-001",
        model_name="seasonal-naive",
        model_version="1.0",
        forecast_payload={"forecast_quantity": 12.0},
        version_number=version_number,
        parent_history_id=parent_history_id,
        created_at_utc=created_at_utc,
        snapshot_id=snapshot_id,
    )


def test_index_lookup_by_snapshot_forecast_and_version():
    index = HistoricalSnapshotIndex()
    first = _record("history-v1")
    second = _record(
        "history-v2",
        version_number=2,
        parent_history_id="history-v1",
        created_at_utc="2026-07-13T11:00:00+00:00",
    )
    other = _record(
        "other-v1",
        forecast_id="forecast-2",
        snapshot_id="snapshot-2",
        created_at_utc="2026-07-13T12:00:00+00:00",
    )

    for record in (first, second, other):
        index.add(record)

    assert index.by_snapshot("snapshot-1") == (first, second)
    assert index.by_forecast("forecast-1") == (first, second)
    assert index.by_version(2) == (second,)
    assert index.get("other-v1") == other


def test_composite_query_and_time_range_are_inclusive():
    index = HistoricalSnapshotIndex(
        (
            _record("early", created_at_utc="2026-07-13T09:00:00+00:00"),
            _record("middle", created_at_utc="2026-07-13T10:00:00+00:00"),
            _record("late", created_at_utc="2026-07-13T11:00:00+00:00"),
        )
    )

    result = index.query(
        HistoryIndexQuery(
            snapshot_id="snapshot-1",
            forecast_id="forecast-1",
            version_number=1,
            created_from_utc="2026-07-13T10:00:00+00:00",
            created_to_utc="2026-07-13T11:00:00+00:00",
        )
    )

    assert tuple(record.history_id for record in result) == ("middle", "late")


def test_exact_timestamp_lookup_normalizes_equivalent_offsets():
    record = _record("history-1", created_at_utc="2026-07-13T10:00:00+00:00")
    index = HistoricalSnapshotIndex((record,))

    result = index.query(HistoryIndexQuery(created_at_utc="2026-07-13T12:00:00+02:00"))

    assert result == (record,)


def test_index_is_tenant_isolated():
    index = HistoricalSnapshotIndex()

    with _tenant("alpha"):
        alpha = _record("shared-id", forecast_id="forecast-alpha")
        index.add(alpha)

    with _tenant("bravo"):
        bravo = _record("shared-id", forecast_id="forecast-bravo")
        index.add(bravo)

    with _tenant("alpha"):
        assert index.get("shared-id") == alpha
        assert index.by_forecast("forecast-bravo") == ()

    with _tenant("bravo"):
        assert index.get("shared-id") == bravo
        assert index.by_forecast("forecast-alpha") == ()


def test_duplicate_history_id_rejected_within_namespace_only():
    index = HistoricalSnapshotIndex()
    record = _record("history-1")
    index.add(record)

    with pytest.raises(ValueError, match="history record already indexed: history-1"):
        index.add(record)

    with _tenant("other"):
        index.add(record)
        assert index.get("history-1") == record


def test_query_validation_rejects_invalid_ranges_and_versions():
    with pytest.raises(ValueError, match="version_number must be greater than or equal to 1"):
        HistoryIndexQuery(version_number=0)

    with pytest.raises(ValueError, match="created_from_utc must not be after created_to_utc"):
        HistoryIndexQuery(
            created_from_utc="2026-07-13T12:00:00+00:00",
            created_to_utc="2026-07-13T11:00:00+00:00",
        )


def test_index_rejects_naive_or_invalid_record_timestamps():
    index = HistoricalSnapshotIndex()

    with pytest.raises(ValueError, match="history index timestamps must include a UTC offset"):
        index.add(_record("naive", created_at_utc="2026-07-13T10:00:00"))

    with pytest.raises(ValueError, match="invalid ISO-8601 timestamp"):
        index.add(_record("invalid", created_at_utc="not-a-timestamp"))
