from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


@dataclass(frozen=True)
class ReportExportResult:
    report_id: str
    report_type: str
    export_format: str
    path: str
    row_count: int
    generated_at_utc: str
    filters: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(cls, report_type: str, export_format: str, path: str, row_count: int, filters: dict[str, Any] | None = None) -> "ReportExportResult":
        return cls(
            report_id=str(uuid4()),
            report_type=report_type,
            export_format=export_format,
            path=path,
            row_count=row_count,
            generated_at_utc=datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
            filters=filters or {},
        )
