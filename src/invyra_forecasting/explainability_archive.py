from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable
from uuid import uuid4

from invyra_forecasting.api.tenant_context import current_request_id
from invyra_forecasting.api.tenant_namespace import current_namespace
from invyra_forecasting.models.contracts import ForecastModelOutput


@dataclass(frozen=True)
class HistoricalExplainabilityRecord:
    """Immutable archive of explainability exactly as generated for one forecast."""

    archive_id: str
    history_id: str
    forecast_id: str
    model_name: str
    model_version: str
    confidence: float
    explanation: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    reasoning_summary: tuple[str, ...] = ()
    supporting_metrics: dict[str, Any] = field(default_factory=dict)
    archived_at_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    advisory_only: bool = True
    read_only: bool = True
    inventory_source_of_truth_preserved: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for field_name, value in {
            "archive_id": self.archive_id,
            "history_id": self.history_id,
            "forecast_id": self.forecast_id,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "archived_at_utc": self.archived_at_utc,
        }.items():
            if not value:
                raise ValueError(f"{field_name} is required")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        if not self.advisory_only:
            raise ValueError("explainability archives must remain advisory-only")
        if not self.read_only:
            raise ValueError("explainability archives must remain read-only")
        if not self.inventory_source_of_truth_preserved:
            raise ValueError("inventory source of truth must be preserved")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["explanation"] = list(self.explanation)
        payload["evidence_refs"] = list(self.evidence_refs)
        payload["reasoning_summary"] = list(self.reasoning_summary)
        return payload


class InMemoryHistoricalExplainabilityRepository:
    """Tenant-isolated, append-only explainability archive."""

    def __init__(self, records: Iterable[HistoricalExplainabilityRecord] = ()) -> None:
        self._records_by_namespace: dict[str, dict[str, HistoricalExplainabilityRecord]] = {}
        for record in records:
            self.append(record)

    def _records(self) -> dict[str, HistoricalExplainabilityRecord]:
        return self._records_by_namespace.setdefault(current_namespace(), {})

    def append(self, record: HistoricalExplainabilityRecord) -> HistoricalExplainabilityRecord:
        records = self._records()
        if record.archive_id in records:
            raise ValueError(f"explainability archive already exists: {record.archive_id}")
        if any(existing.history_id == record.history_id for existing in records.values()):
            raise ValueError(f"history record already has explainability archived: {record.history_id}")
        records[record.archive_id] = record
        return record

    def get(self, archive_id: str) -> HistoricalExplainabilityRecord | None:
        return self._records().get(archive_id)

    def for_history(self, history_id: str) -> HistoricalExplainabilityRecord | None:
        return next((record for record in self._records().values() if record.history_id == history_id), None)

    def for_forecast(self, forecast_id: str) -> tuple[HistoricalExplainabilityRecord, ...]:
        return tuple(
            sorted(
                (record for record in self._records().values() if record.forecast_id == forecast_id),
                key=lambda record: (record.archived_at_utc, record.archive_id),
            )
        )


class HistoricalExplainabilityArchiveService:
    def __init__(self, repository: InMemoryHistoricalExplainabilityRepository | None = None) -> None:
        self._repository = repository or InMemoryHistoricalExplainabilityRepository()

    def archive_output(
        self,
        *,
        history_id: str,
        forecast_id: str,
        output: ForecastModelOutput,
        archive_id: str | None = None,
        reasoning_summary: Iterable[str] = (),
        supporting_metrics: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> HistoricalExplainabilityRecord:
        archive_metadata = dict(metadata or {})
        request_id = current_request_id()
        if request_id is not None:
            archive_metadata.setdefault("request_id", request_id)
        record = HistoricalExplainabilityRecord(
            archive_id=archive_id or str(uuid4()),
            history_id=history_id,
            forecast_id=forecast_id,
            model_name=output.model_name,
            model_version=output.model_version,
            confidence=output.confidence,
            explanation=tuple(output.explanation),
            evidence_refs=tuple(output.evidence_refs),
            reasoning_summary=tuple(reasoning_summary),
            supporting_metrics=dict(supporting_metrics or {}),
            metadata=archive_metadata,
        )
        return self._repository.append(record)

    def get(self, archive_id: str) -> HistoricalExplainabilityRecord | None:
        return self._repository.get(archive_id)

    def for_history(self, history_id: str) -> HistoricalExplainabilityRecord | None:
        return self._repository.for_history(history_id)

    def for_forecast(self, forecast_id: str) -> tuple[HistoricalExplainabilityRecord, ...]:
        return self._repository.for_forecast(forecast_id)
