from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import quote

from invyra_forecasting.api.tenant_namespace import DEFAULT_NAMESPACE, current_namespace
from invyra_forecasting.explainability_archive import HistoricalExplainabilityRecord


class FileHistoricalExplainabilityRepository:
    """Tenant-isolated, append-only file storage for explainability archives."""

    def __init__(self, archive_dir: str | Path = "data/explainability") -> None:
        self.archive_dir = Path(archive_dir)

    def namespace_dir(self) -> Path:
        namespace = current_namespace()
        if namespace == DEFAULT_NAMESPACE:
            return self.archive_dir
        return self.archive_dir / quote(namespace, safe="-_.")

    def path_for(self, archive_id: str) -> Path:
        safe_id = archive_id.replace("/", "_").replace("\\", "_")
        return self.namespace_dir() / f"{safe_id}.json"

    def append(self, record: HistoricalExplainabilityRecord) -> HistoricalExplainabilityRecord:
        destination = self.path_for(record.archive_id)
        if destination.exists():
            raise ValueError(f"explainability archive already exists: {record.archive_id}")
        if self.for_history(record.history_id) is not None:
            raise ValueError(
                f"history record already has explainability archived: {record.history_id}"
            )

        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(record.to_dict(), indent=2, sort_keys=True, default=str),
            encoding="utf-8",
        )
        temporary.replace(destination)
        return record

    def get(self, archive_id: str) -> HistoricalExplainabilityRecord | None:
        path = self.path_for(archive_id)
        if not path.exists():
            return None
        return self._decode(path)

    def all(self) -> tuple[HistoricalExplainabilityRecord, ...]:
        directory = self.namespace_dir()
        if not directory.exists():
            return ()
        records = tuple(self._decode(path) for path in directory.glob("*.json"))
        return tuple(
            sorted(records, key=lambda record: (record.archived_at_utc, record.archive_id))
        )

    def for_history(self, history_id: str) -> HistoricalExplainabilityRecord | None:
        return next((record for record in self.all() if record.history_id == history_id), None)

    def for_forecast(self, forecast_id: str) -> tuple[HistoricalExplainabilityRecord, ...]:
        return tuple(record for record in self.all() if record.forecast_id == forecast_id)

    def load_into(self, repository) -> int:
        count = 0
        for record in self.all():
            repository.append(record)
            count += 1
        return count

    def _decode(self, path: Path) -> HistoricalExplainabilityRecord:
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["explanation"] = tuple(payload.get("explanation", ()))
        payload["evidence_refs"] = tuple(payload.get("evidence_refs", ()))
        payload["reasoning_summary"] = tuple(payload.get("reasoning_summary", ()))
        payload["supporting_metrics"] = dict(payload.get("supporting_metrics", {}))
        return HistoricalExplainabilityRecord(**payload)
