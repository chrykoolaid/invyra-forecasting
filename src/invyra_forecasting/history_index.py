from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from invyra_forecasting.api.tenant_namespace import current_namespace
from invyra_forecasting.history import ForecastHistoryRecord


@dataclass(frozen=True)
class HistoryIndexQuery:
    history_id: str | None = None
    snapshot_id: str | None = None
    forecast_id: str | None = None
    version_number: int | None = None
    created_at_utc: str | None = None
    created_from_utc: str | None = None
    created_to_utc: str | None = None

    def __post_init__(self) -> None:
        if self.version_number is not None and self.version_number < 1:
            raise ValueError("version_number must be greater than or equal to 1")
        if self.created_from_utc and self.created_to_utc:
            if _parse_timestamp(self.created_from_utc) > _parse_timestamp(self.created_to_utc):
                raise ValueError("created_from_utc must not be after created_to_utc")


class HistoricalSnapshotIndex:
    """Tenant-isolated internal index over immutable forecast history records."""

    def __init__(self, records: Iterable[ForecastHistoryRecord] = ()) -> None:
        self._records_by_namespace: dict[str, dict[str, ForecastHistoryRecord]] = {}
        self._history_ids_by_snapshot: dict[str, dict[str, set[str]]] = {}
        self._history_ids_by_forecast: dict[str, dict[str, set[str]]] = {}
        self._history_ids_by_version: dict[str, dict[int, set[str]]] = {}
        for record in records:
            self.add(record)

    def _records(self) -> dict[str, ForecastHistoryRecord]:
        return self._records_by_namespace.setdefault(current_namespace(), {})

    def _snapshot_index(self) -> dict[str, set[str]]:
        return self._history_ids_by_snapshot.setdefault(current_namespace(), {})

    def _forecast_index(self) -> dict[str, set[str]]:
        return self._history_ids_by_forecast.setdefault(current_namespace(), {})

    def _version_index(self) -> dict[int, set[str]]:
        return self._history_ids_by_version.setdefault(current_namespace(), {})

    def add(self, record: ForecastHistoryRecord) -> ForecastHistoryRecord:
        records = self._records()
        if record.history_id in records:
            raise ValueError(f"history record already indexed: {record.history_id}")
        _parse_timestamp(record.created_at_utc)
        records[record.history_id] = record
        if record.snapshot_id is not None:
            self._snapshot_index().setdefault(record.snapshot_id, set()).add(record.history_id)
        self._forecast_index().setdefault(record.forecast_id, set()).add(record.history_id)
        self._version_index().setdefault(record.version_number, set()).add(record.history_id)
        return record

    def get(self, history_id: str) -> ForecastHistoryRecord | None:
        return self._records().get(history_id)

    def by_snapshot(self, snapshot_id: str) -> tuple[ForecastHistoryRecord, ...]:
        return self._resolve(self._snapshot_index().get(snapshot_id, set()))

    def by_forecast(self, forecast_id: str) -> tuple[ForecastHistoryRecord, ...]:
        return self._resolve(self._forecast_index().get(forecast_id, set()))

    def by_version(self, version_number: int) -> tuple[ForecastHistoryRecord, ...]:
        if version_number < 1:
            raise ValueError("version_number must be greater than or equal to 1")
        return self._resolve(self._version_index().get(version_number, set()))

    def query(self, query: HistoryIndexQuery) -> tuple[ForecastHistoryRecord, ...]:
        candidate_ids = set(self._records())
        if query.history_id is not None:
            candidate_ids &= {query.history_id}
        if query.snapshot_id is not None:
            candidate_ids &= self._snapshot_index().get(query.snapshot_id, set())
        if query.forecast_id is not None:
            candidate_ids &= self._forecast_index().get(query.forecast_id, set())
        if query.version_number is not None:
            candidate_ids &= self._version_index().get(query.version_number, set())

        records = self._resolve(candidate_ids)
        if query.created_at_utc is not None:
            exact = _parse_timestamp(query.created_at_utc)
            records = tuple(record for record in records if _parse_timestamp(record.created_at_utc) == exact)
        if query.created_from_utc is not None:
            lower = _parse_timestamp(query.created_from_utc)
            records = tuple(record for record in records if _parse_timestamp(record.created_at_utc) >= lower)
        if query.created_to_utc is not None:
            upper = _parse_timestamp(query.created_to_utc)
            records = tuple(record for record in records if _parse_timestamp(record.created_at_utc) <= upper)
        return records

    def _resolve(self, history_ids: set[str]) -> tuple[ForecastHistoryRecord, ...]:
        records = self._records()
        return tuple(
            sorted(
                (records[history_id] for history_id in history_ids if history_id in records),
                key=lambda record: (record.created_at_utc, record.history_id),
            )
        )


def _parse_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"invalid ISO-8601 timestamp: {value}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("history index timestamps must include a UTC offset")
    return parsed
