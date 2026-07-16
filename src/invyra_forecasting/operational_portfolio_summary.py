from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Iterable

from invyra_forecasting.api.tenant_namespace import current_namespace
from invyra_forecasting.history import ForecastHistoryRecord

OPERATIONAL_PORTFOLIO_SUMMARY_SCHEMA_VERSION = "1.0.0"


@dataclass(frozen=True)
class OperationalForecastPortfolioSummary:
    namespace: str
    as_of_utc: str
    forecast_record_count: int
    unique_item_count: int
    unique_location_count: int
    unique_item_location_count: int
    evidence_linked_record_count: int
    snapshot_linked_record_count: int
    model_usage_distribution: tuple[tuple[str, int], ...]
    history_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    schema_version: str = OPERATIONAL_PORTFOLIO_SUMMARY_SCHEMA_VERSION
    advisory_only: bool = True
    read_only: bool = True
    inventory_source_of_truth_preserved: bool = True

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["model_usage_distribution"] = dict(self.model_usage_distribution)
        payload["history_refs"] = list(self.history_refs)
        payload["evidence_refs"] = list(self.evidence_refs)
        return payload


class OperationalForecastPortfolioSummaryService:
    """Aggregates immutable forecast history without recalculating forecasts or inventory state."""

    def summarize(
        self,
        records: Iterable[ForecastHistoryRecord],
        *,
        as_of_utc: str,
    ) -> OperationalForecastPortfolioSummary:
        cutoff = _parse_timestamp(as_of_utc)
        eligible: list[ForecastHistoryRecord] = []
        for record in records:
            if not record.advisory_only or not record.read_only:
                raise ValueError("operational portfolio inputs must remain advisory-only and read-only")
            if not record.inventory_source_of_truth_preserved:
                raise ValueError("inventory source of truth must be preserved")
            if _parse_timestamp(record.created_at_utc) <= cutoff:
                eligible.append(record)

        eligible.sort(key=lambda record: (record.created_at_utc, record.history_id))
        items = {record.item_id for record in eligible}
        locations = {record.location_id for record in eligible}
        item_locations = {(record.item_id, record.location_id) for record in eligible}
        model_usage: dict[str, int] = {}
        for record in eligible:
            identity = f"{record.model_name}:{record.model_version}"
            model_usage[identity] = model_usage.get(identity, 0) + 1

        return OperationalForecastPortfolioSummary(
            namespace=current_namespace(),
            as_of_utc=as_of_utc,
            forecast_record_count=len(eligible),
            unique_item_count=len(items),
            unique_location_count=len(locations),
            unique_item_location_count=len(item_locations),
            evidence_linked_record_count=sum(bool(record.evidence_refs) for record in eligible),
            snapshot_linked_record_count=sum(record.snapshot_id is not None for record in eligible),
            model_usage_distribution=tuple(sorted(model_usage.items())),
            history_refs=tuple(record.history_id for record in eligible),
            evidence_refs=tuple(sorted({ref for record in eligible for ref in record.evidence_refs})),
        )


def _parse_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("operational portfolio timestamps must be valid ISO-8601 timestamps") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("operational portfolio timestamps must include a UTC offset")
    return parsed
