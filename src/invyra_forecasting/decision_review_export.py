from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from invyra_forecasting.decision_review_api import DecisionReviewApiResponse


@dataclass(frozen=True)
class DecisionReviewExportProjection:
    """Read-only export payload for forecast decision review responses."""

    response: DecisionReviewApiResponse
    export_format: str = "json"
    export_version: str = "8I.1"
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "export_format": self.export_format,
            "export_version": self.export_version,
            "response": self.response.to_dict(),
            "generated_at": self.generated_at,
            "advisory_only": True,
            "read_only": True,
            "inventory_source_of_truth_preserved": True,
        }


class DecisionReviewExportProjectionBuilder:
    """Builds stable read-only export projections for forecast review payloads."""

    def build(
        self,
        response: DecisionReviewApiResponse,
        *,
        export_format: str = "json",
    ) -> DecisionReviewExportProjection:
        normalized_format = export_format.lower().strip()
        if normalized_format not in {"json", "dict"}:
            raise ValueError("Unsupported decision review export format")
        return DecisionReviewExportProjection(response=response, export_format=normalized_format)
