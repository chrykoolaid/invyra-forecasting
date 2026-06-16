from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ReportExportRequest(BaseModel):
    report_type: Literal["summary", "snapshots", "accuracy", "audit", "confidence"] = "summary"
    export_format: Literal["json", "csv"] = "json"
    item_id: str | None = None
    location_id: str | None = None
    environment: str | None = None
    limit: int = Field(default=100, ge=1, le=10000)
