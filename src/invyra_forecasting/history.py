from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable
from uuid import uuid4

from invyra_forecasting.api.tenant_context import current_request_id
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
    version_number: int = 1
    parent_history_id: str | None = None
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
        if self.version_number < 1:
            raise ValueError("version_number must be greater than or equal to 1")
        if self.version_number == 1 and self.parent_history_id is not None:
            raise ValueError("version 1 cannot have a parent history record")
        if self.version_number > 1 and not self.parent_history_id:
            raise ValueError("versioned history records require a parent_history_id")
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
        if any(
            existing.forecast_id == record.forecast_id
            and existing.version_number == record.version_number
            for existing in records.values()
        ):
            raise ValueError(
                f"forecast history version already exists: {record.forecast_id} v{record.version_number}"
            )
        if record.parent_history_id is not None:
            parent = records.get(record.parent_history_id)
            if parent is None:
                raise ValueError(f"parent history record does not exist: {record.parent_history_id}")
            if parent.forecast_id != record.forecast_id:
                raise ValueError("parent history record must belong to the same forecast")
            if parent.version_number + 1 != record.version_number:
                raise ValueError("history version must directly follow its parent version")
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

    def versions_for_forecast(self, forecast_id: str) -> tuple[ForecastHistoryRecord, ...]:
        return tuple(
            sorted(
                (
                    record
                    for record in self._records().values()
                    if record.forecast_id == forecast_id
                ),
                key=lambda record: record.version_number,
            )
        )

    def latest_for_forecast(self, forecast_id: str) -> ForecastHistoryRecord | None:
        versions = self.versions_for_forecast(forecast_id)
        return versions[-1] if versions else None

    def lineage(self, history_id: str) -> tuple[ForecastHistoryRecord, ...]:
        record = self.get(history_id)
        if record is None:
            return ()
        lineage: list[ForecastHistoryRecord] = [record]
        while lineage[-1].parent_history_id is not None:
            parent = self.get(lineage[-1].parent_history_id)
            if parent is None:
                raise ValueError("history lineage is incomplete")
            lineage.append(parent)
        return tuple(reversed(lineage))


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
        version_number: int = 1,
        parent_history_id: str | None = None,
        snapshot_id: str | None = None,
        evidence_refs: Iterable[str] = (),
        metadata: dict[str, Any] | None = None,
    ) -> ForecastHistoryRecord:
        record_metadata = dict(metadata or {})
        request_id = current_request_id()
        if request_id is not None:
            record_metadata.setdefault("request_id", request_id)

        record = ForecastHistoryRecord(
            history_id=history_id or str(uuid4()),
            forecast_id=forecast_id,
            item_id=item_id,
            location_id=location_id,
            model_name=model_name,
            model_version=model_version,
            forecast_payload=dict(forecast_payload),
            version_number=version_number,
            parent_history_id=parent_history_id,
            snapshot_id=snapshot_id,
            evidence_refs=tuple(evidence_refs),
            metadata=record_metadata,
        )
        return self._repository.append(record)

    def revise(
        self,
        parent_history_id: str,
        *,
        forecast_payload: dict[str, Any],
        history_id: str | None = None,
        snapshot_id: str | None = None,
        evidence_refs: Iterable[str] = (),
        metadata: dict[str, Any] | None = None,
    ) -> ForecastHistoryRecord:
        parent = self._repository.get(parent_history_id)
        if parent is None:
            raise ValueError(f"parent history record does not exist: {parent_history_id}")
        return self.record(
            history_id=history_id,
            forecast_id=parent.forecast_id,
            item_id=parent.item_id,
            location_id=parent.location_id,
            model_name=parent.model_name,
            model_version=parent.model_version,
            forecast_payload=forecast_payload,
            version_number=parent.version_number + 1,
            parent_history_id=parent.history_id,
            snapshot_id=snapshot_id,
            evidence_refs=evidence_refs,
            metadata=metadata,
        )

    def get(self, history_id: str) -> ForecastHistoryRecord | None:
        return self._repository.get(history_id)

    def all(self) -> tuple[ForecastHistoryRecord, ...]:
        return self._repository.all()

    def versions_for_forecast(self, forecast_id: str) -> tuple[ForecastHistoryRecord, ...]:
        return self._repository.versions_for_forecast(forecast_id)

    def latest_for_forecast(self, forecast_id: str) -> ForecastHistoryRecord | None:
        return self._repository.latest_for_forecast(forecast_id)

    def lineage(self, history_id: str) -> tuple[ForecastHistoryRecord, ...]:
        return self._repository.lineage(history_id)
