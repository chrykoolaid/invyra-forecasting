from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable
from urllib.parse import quote

from invyra_forecasting.api.tenant_namespace import DEFAULT_NAMESPACE, current_namespace
from invyra_forecasting.history import ForecastHistoryRecord


class FileForecastHistoryRepository:
    """Tenant-isolated, append-only file storage for immutable history records."""

    def __init__(self, history_dir: str | Path = "data/history") -> None:
        self.history_dir = Path(history_dir)

    def namespace_dir(self) -> Path:
        namespace = current_namespace()
        if namespace == DEFAULT_NAMESPACE:
            return self.history_dir
        return self.history_dir / quote(namespace, safe="-_.")

    def path_for(self, history_id: str) -> Path:
        safe_id = history_id.replace("/", "_").replace("\\", "_")
        return self.namespace_dir() / f"{safe_id}.json"

    def append(self, record: ForecastHistoryRecord) -> ForecastHistoryRecord:
        destination = self.path_for(record.history_id)
        if destination.exists():
            raise ValueError(f"history record already exists: {record.history_id}")

        existing = self.all()
        if any(
            item.forecast_id == record.forecast_id
            and item.version_number == record.version_number
            for item in existing
        ):
            raise ValueError(
                f"forecast history version already exists: {record.forecast_id} v{record.version_number}"
            )

        if record.parent_history_id is not None:
            parent = self.get(record.parent_history_id)
            if parent is None:
                raise ValueError(f"parent history record does not exist: {record.parent_history_id}")
            if parent.forecast_id != record.forecast_id:
                raise ValueError("parent history record must belong to the same forecast")
            if parent.version_number + 1 != record.version_number:
                raise ValueError("history version must directly follow its parent version")

        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(record.to_dict(), indent=2, sort_keys=True, default=str),
            encoding="utf-8",
        )
        temporary.replace(destination)
        return record

    def get(self, history_id: str) -> ForecastHistoryRecord | None:
        path = self.path_for(history_id)
        if not path.exists():
            return None
        return self._decode(path)

    def all(self) -> tuple[ForecastHistoryRecord, ...]:
        directory = self.namespace_dir()
        if not directory.exists():
            return ()
        records = tuple(self._decode(path) for path in directory.glob("*.json"))
        return tuple(sorted(records, key=lambda item: (item.created_at_utc, item.history_id)))

    def versions_for_forecast(self, forecast_id: str) -> tuple[ForecastHistoryRecord, ...]:
        return tuple(
            sorted(
                (record for record in self.all() if record.forecast_id == forecast_id),
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

    def load_into(self, repository) -> int:
        """Load the active namespace into any append-compatible repository."""
        count = 0
        for record in self.all():
            repository.append(record)
            count += 1
        return count

    def _decode(self, path: Path) -> ForecastHistoryRecord:
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["evidence_refs"] = tuple(payload.get("evidence_refs", ()))
        payload["forecast_payload"] = dict(payload.get("forecast_payload", {}))
        payload["metadata"] = dict(payload.get("metadata", {}))
        return ForecastHistoryRecord(**payload)
