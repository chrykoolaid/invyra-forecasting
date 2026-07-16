from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Iterable

from invyra_forecasting.api.tenant_namespace import current_namespace
from invyra_forecasting.history import ForecastHistoryRecord

OPERATIONAL_PORTFOLIO_BREAKDOWN_SCHEMA_VERSION = "1.0.0"


@dataclass(frozen=True)
class OperationalPortfolioBreakdownEntry:
    item_id: str | None
    location_id: str | None
    forecast_record_count: int
    evidence_linked_record_count: int
    snapshot_linked_record_count: int
    earliest_forecast_at_utc: str
    latest_forecast_at_utc: str
    history_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["history_refs"] = list(self.history_refs)
        payload["evidence_refs"] = list(self.evidence_refs)
        return payload


@dataclass(frozen=True)
class OperationalForecastPortfolioBreakdown:
    namespace: str
    as_of_utc: str
    items: tuple[OperationalPortfolioBreakdownEntry, ...]
    locations: tuple[OperationalPortfolioBreakdownEntry, ...]
    item_locations: tuple[OperationalPortfolioBreakdownEntry, ...]
    schema_version: str = OPERATIONAL_PORTFOLIO_BREAKDOWN_SCHEMA_VERSION
    advisory_only: bool = True
    read_only: bool = True
    inventory_source_of_truth_preserved: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "namespace": self.namespace,
            "as_of_utc": self.as_of_utc,
            "items": [entry.to_dict() for entry in self.items],
            "locations": [entry.to_dict() for entry in self.locations],
            "item_locations": [entry.to_dict() for entry in self.item_locations],
            "schema_version": self.schema_version,
            "advisory_only": self.advisory_only,
            "read_only": self.read_only,
            "inventory_source_of_truth_preserved": self.inventory_source_of_truth_preserved,
        }


class OperationalForecastPortfolioBreakdownService:
    """Builds deterministic item and location views from immutable forecast history."""

    def breakdown(
        self,
        records: Iterable[ForecastHistoryRecord],
        *,
        as_of_utc: str,
    ) -> OperationalForecastPortfolioBreakdown:
        cutoff = _parse_timestamp(as_of_utc)
        eligible: list[ForecastHistoryRecord] = []
        for record in records:
            _validate_record(record)
            if _parse_timestamp(record.created_at_utc) <= cutoff:
                eligible.append(record)
        eligible.sort(key=lambda record: (record.created_at_utc, record.history_id))

        item_groups: dict[tuple[str | None, str | None], list[ForecastHistoryRecord]] = {}
        location_groups: dict[tuple[str | None, str | None], list[ForecastHistoryRecord]] = {}
        pair_groups: dict[tuple[str | None, str | None], list[ForecastHistoryRecord]] = {}
        for record in eligible:
            item_groups.setdefault((record.item_id, None), []).append(record)
            location_groups.setdefault((None, record.location_id), []).append(record)
            pair_groups.setdefault((record.item_id, record.location_id), []).append(record)

        return OperationalForecastPortfolioBreakdown(
            namespace=current_namespace(),
            as_of_utc=as_of_utc,
            items=_entries(item_groups),
            locations=_entries(location_groups),
            item_locations=_entries(pair_groups),
        )


def _entries(
    groups: dict[tuple[str | None, str | None], list[ForecastHistoryRecord]],
) -> tuple[OperationalPortfolioBreakdownEntry, ...]:
    entries: list[OperationalPortfolioBreakdownEntry] = []
    for (item_id, location_id), records in sorted(groups.items(), key=lambda item: item[0]):
        entries.append(
            OperationalPortfolioBreakdownEntry(
                item_id=item_id,
                location_id=location_id,
                forecast_record_count=len(records),
                evidence_linked_record_count=sum(bool(record.evidence_refs) for record in records),
                snapshot_linked_record_count=sum(record.snapshot_id is not None for record in records),
                earliest_forecast_at_utc=records[0].created_at_utc,
                latest_forecast_at_utc=records[-1].created_at_utc,
                history_refs=tuple(record.history_id for record in records),
                evidence_refs=tuple(sorted({ref for record in records for ref in record.evidence_refs})),
            )
        )
    return tuple(entries)


def _validate_record(record: ForecastHistoryRecord) -> None:
    if not record.advisory_only or not record.read_only:
        raise ValueError("operational portfolio inputs must remain advisory-only and read-only")
    if not record.inventory_source_of_truth_preserved:
        raise ValueError("inventory source of truth must be preserved")


def _parse_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("operational portfolio timestamps must be valid ISO-8601 timestamps") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("operational portfolio timestamps must include a UTC offset")
    return parsed
