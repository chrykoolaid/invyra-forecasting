from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable
from uuid import uuid4

from invyra_forecasting.api.tenant_namespace import current_namespace


@dataclass(frozen=True)
class ForecastHistoryRecord:
    """Immutable historical record of one completed forecast result."""

    history_id: str
    forecast_id: str
    item_id: str
    location_id: str
    model_name: str
    model_version: str
    forecast_payload: dict[str, Any]
    created_at_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    snapshot_id: str | None = None
    evidence_refs: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    advisory_only: bool = True
    read_only: bool = True
    inventory_source_of_truth_preserved: bool = True

    def __post_init__(self) -> None:
        required = {
            "history_id": self.history_id,
            "forecast_id": self.forecast_id,
            "item_id": self.item_id,
            "location_id": self.location_id,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "created_at_utc": self.created_at_utc,
        }
        for field_name, value in required.items():
            if not value:
                raise ValueError(f"{field_name} is required")
        if not self.advisory_only:
            raise ValueError("history records must remain advisory-only")
        if not self.read_only:
            raise ValueError("history records must remain read-only")
        if not self.inventory_source_of_truth_preserved:
            raise ValueError("inventory source of truth must be preserved")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["evidence_refs"] = list(self.evidence_refs)
        return payload


class InMemoryForecastHistoryRepository:
    """Tenant-isolated, append-only storage for immutable history records."""

    def __init__(self, records: Iterable[ForecastHistoryRecord] = ()) -> None:
        self._records_by_namespace: dict[str, dict[str, ForecastHistoryRecord]] = {}
        for record in records:
            self.append(record)

    def _records(self) -> dict[str, ForecastHistoryRecord]:
        return self._records_by_namespace.setdefault(current_namespace(), {})

    def append(self, record: ForecastHistoryRecord) -> ForecastHistoryRecord:
        records = self._records()
        if record.history_id in records:
            raise ValueError(f"history record already exists: {record.history_id}")
        records[record.history_id] = record
        return record

    def get(self, history_id: str) -> ForecastHistoryRecord | None:
        return self._records().get(history_id)

    def all(self) -> tuple[ForecastHistoryRecord, ...]:
        return tuple(
            sorted(
                self._records().values(),
                key=lambda record: (record.created_at_utc, record.history_id),
            )
        )


class ForecastHistoryService:
    def __init__(self, repository: InMemoryForecastHistoryRepository | None = None) -> None:
        self._repository = repository or InMemoryForecastHistoryRepository()

    def record(
        self,
        *,
        forecast_id: str,
        item_id: str,
        location_id: str,
        model_name: str,
        model_version: str,
        forecast_payload: dict[str, Any],
        history_id: str | None = None,
        snapshot_id: str | None = None,
        evidence_refs: Iterable[str] = (),
        metadata: dict[str, Any] | None = None,
    ) -> ForecastHistoryRecord:
        record = ForecastHistoryRecord(
            history_id=history_id or str(uuid4()),
            forecast_id=forecast_id,
            item_id=item_id,
            location_id=location_id,
            model_name=model_name,
            model_version=model_version,
            forecast_payload=dict(forecast_payload),
            snapshot_id=snapshot_id,
            evidence_refs=tuple(evidence_refs),
            metadata=dict(metadata or {}),
        )
        return self._repository.append(record)

    def get(self, history_id: str) -> ForecastHistoryRecord | None:
        return self._repository.get(history_id)

    def all(self) -> tuple[ForecastHistoryRecord, ...]:
        return self._repository.all()
