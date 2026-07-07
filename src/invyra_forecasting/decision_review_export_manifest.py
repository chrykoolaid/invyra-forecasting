from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from invyra_forecasting.decision_review_export import DecisionReviewExportProjection


@dataclass(frozen=True)
class DecisionReviewExportManifest:
    """Read-only manifest metadata for a forecast decision review export."""

    export: DecisionReviewExportProjection
    manifest_version: str = "8J.1"
    record_count: int = 0
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest_version": self.manifest_version,
            "record_count": self.record_count,
            "export": self.export.to_dict(),
            "generated_at": self.generated_at,
            "advisory_only": True,
            "read_only": True,
            "inventory_source_of_truth_preserved": True,
        }


class DecisionReviewExportManifestBuilder:
    """Builds read-only export manifests without writing or transmitting files."""

    def build(self, export: DecisionReviewExportProjection) -> DecisionReviewExportManifest:
        payload = export.to_dict()
        dashboard = payload.get("response", {}).get("dashboard", {}) if isinstance(payload.get("response"), dict) else {}
        summary = dashboard.get("summary", {}) if isinstance(dashboard, dict) else {}
        total_count = summary.get("total_count", 0) if isinstance(summary, dict) else 0
        record_count = int(total_count) if isinstance(total_count, int) else 0
        return DecisionReviewExportManifest(export=export, record_count=record_count)
