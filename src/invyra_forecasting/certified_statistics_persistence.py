from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from invyra_forecasting.api.tenant_namespace import current_namespace
from invyra_forecasting.model_performance_statistics import ModelPerformanceStatistics

CERTIFIED_STATISTICS_RECORD_SCHEMA_VERSION = "1.0.0"


@dataclass(frozen=True)
class CertifiedModelPerformanceStatisticsRecord:
    record_id: str
    namespace: str
    statistics: ModelPerformanceStatistics
    evidence_refs: tuple[str, ...]
    certified_at_utc: str
    schema_version: str = CERTIFIED_STATISTICS_RECORD_SCHEMA_VERSION
    advisory_only: bool = True
    read_only: bool = True
    inventory_source_of_truth_preserved: bool = True

    def __post_init__(self) -> None:
        if not self.record_id or not self.namespace:
            raise ValueError("record_id and namespace are required")
        _parse_timestamp(self.certified_at_utc)
        if self.statistics.eligible_evaluation_count > 0 and not self.evidence_refs:
            raise ValueError("certified statistics with evaluations require evidence references")
        if any(not isinstance(ref, str) or not ref.strip() for ref in self.evidence_refs):
            raise ValueError("evidence references must contain non-empty strings")
        if len(set(self.evidence_refs)) != len(self.evidence_refs):
            raise ValueError("evidence references must be unique")
        if self.schema_version != CERTIFIED_STATISTICS_RECORD_SCHEMA_VERSION:
            raise ValueError("unsupported certified statistics record schema version")
        if not self.statistics.advisory_only or not self.statistics.read_only:
            raise ValueError("certified statistics must remain advisory-only and read-only")
        if not self.statistics.inventory_source_of_truth_preserved:
            raise ValueError("inventory source of truth must be preserved")
        if not self.advisory_only or not self.read_only:
            raise ValueError("certified statistics records must remain advisory-only and read-only")
        if not self.inventory_source_of_truth_preserved:
            raise ValueError("inventory source of truth must be preserved")

    @property
    def identity(self) -> tuple[str, int | None]:
        return self.statistics.registry_id, self.statistics.forecast_horizon_days

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["statistics"] = self.statistics.to_dict()
        payload["evidence_refs"] = list(self.evidence_refs)
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "CertifiedModelPerformanceStatisticsRecord":
        return cls(
            **{
                **payload,
                "statistics": ModelPerformanceStatistics(**payload["statistics"]),
                "evidence_refs": tuple(payload.get("evidence_refs", ())),
            }
        )


class InMemoryCertifiedStatisticsRepository:
    """Tenant-isolated append-only certified statistics snapshots."""

    def __init__(
        self,
        records: Iterable[CertifiedModelPerformanceStatisticsRecord] = (),
    ) -> None:
        self._records_by_namespace: dict[
            str, dict[str, CertifiedModelPerformanceStatisticsRecord]
        ] = {}
        for record in records:
            self._append_loaded(record)

    def _records(self) -> dict[str, CertifiedModelPerformanceStatisticsRecord]:
        return self._records_by_namespace.setdefault(current_namespace(), {})

    def _append_loaded(self, record: CertifiedModelPerformanceStatisticsRecord) -> None:
        records = self._records_by_namespace.setdefault(record.namespace, {})
        if record.record_id in records:
            raise ValueError(f"certified statistics record already exists: {record.record_id}")
        records[record.record_id] = record

    def append(
        self,
        record: CertifiedModelPerformanceStatisticsRecord,
    ) -> CertifiedModelPerformanceStatisticsRecord:
        if record.namespace != current_namespace():
            raise ValueError("certified statistics namespace must match the active tenant namespace")
        records = self._records()
        if record.record_id in records:
            raise ValueError(f"certified statistics record already exists: {record.record_id}")
        records[record.record_id] = record
        return record

    def all(self) -> tuple[CertifiedModelPerformanceStatisticsRecord, ...]:
        return tuple(
            sorted(
                self._records().values(),
                key=lambda record: (record.certified_at_utc, record.record_id),
            )
        )

    def latest_by_identity(self) -> tuple[CertifiedModelPerformanceStatisticsRecord, ...]:
        latest: dict[tuple[str, int | None], CertifiedModelPerformanceStatisticsRecord] = {}
        for record in self.all():
            existing = latest.get(record.identity)
            if existing is None or (record.certified_at_utc, record.record_id) > (
                existing.certified_at_utc,
                existing.record_id,
            ):
                latest[record.identity] = record
        return tuple(
            sorted(
                latest.values(),
                key=lambda record: (
                    record.statistics.model_name,
                    record.statistics.model_version,
                    record.statistics.forecast_horizon_days or 0,
                    record.record_id,
                ),
            )
        )


class JsonlCertifiedStatisticsRepository(InMemoryCertifiedStatisticsRepository):
    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        records: list[CertifiedModelPerformanceStatisticsRecord] = []
        if self._path.exists():
            for line in self._path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    records.append(
                        CertifiedModelPerformanceStatisticsRecord.from_dict(json.loads(line))
                    )
        super().__init__(records)

    def append(
        self,
        record: CertifiedModelPerformanceStatisticsRecord,
    ) -> CertifiedModelPerformanceStatisticsRecord:
        saved = super().append(record)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(saved.to_dict(), sort_keys=True) + "\n")
        return saved


def _parse_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("certified_at_utc must be a valid ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("certified_at_utc must include a UTC offset")
    return parsed
