from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from invyra_forecasting.constants import Environment
from invyra_forecasting.schemas import AuditEvent


class JsonlAuditStore:
    """Append-only JSONL audit store for Phase 1D."""

    def __init__(self, audit_log_path: str | Path = "data/snapshots/audit_events.jsonl") -> None:
        self.audit_log_path = Path(audit_log_path)

    def append(self, event: AuditEvent) -> Path:
        self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.audit_log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(event), default=str) + "\n")
        return self.audit_log_path

    def list_events(
        self,
        limit: int | None = 100,
        event_type: str | None = None,
        item_id: str | None = None,
        location_id: str | None = None,
        environment: Environment | str | None = None,
    ) -> list[dict[str, Any]]:
        if not self.audit_log_path.exists():
            return []
        environment_value = environment.value if isinstance(environment, Environment) else environment
        events: list[dict[str, Any]] = []
        for line in self.audit_log_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            event = json.loads(line)
            if event_type and event.get("event_type") != event_type:
                continue
            if item_id and event.get("item_id") != item_id:
                continue
            if location_id and event.get("location_id") != location_id:
                continue
            if environment_value and event.get("environment") != environment_value:
                continue
            events.append(event)
        if limit is None or limit <= 0:
            return events
        return events[-limit:]
