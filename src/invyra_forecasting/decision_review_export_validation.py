from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from invyra_forecasting.decision_review_export_manifest import DecisionReviewExportManifest


@dataclass(frozen=True)
class DecisionReviewExportValidationResult:
    """Read-only validation result for forecast decision review export manifests."""

    valid: bool
    warnings: tuple[str, ...]
    validation_version: str = "8K.1"
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "warnings": list(self.warnings),
            "validation_version": self.validation_version,
            "generated_at": self.generated_at,
            "advisory_only": True,
            "read_only": True,
            "inventory_source_of_truth_preserved": True,
        }


class DecisionReviewExportManifestValidator:
    """Validates read-only export manifest consistency without operational mutation."""

    def validate(self, manifest: DecisionReviewExportManifest) -> DecisionReviewExportValidationResult:
        payload = manifest.to_dict()
        warnings: list[str] = []

        if payload.get("advisory_only") is not True:
            warnings.append("Manifest is not marked advisory-only.")
        if payload.get("read_only") is not True:
            warnings.append("Manifest is not marked read-only.")
        if payload.get("inventory_source_of_truth_preserved") is not True:
            warnings.append("Manifest does not preserve Inventory as source of truth.")

        export_payload = payload.get("export", {})
        if not isinstance(export_payload, dict):
            warnings.append("Manifest export payload is not a dictionary.")
        else:
            if export_payload.get("advisory_only") is not True:
                warnings.append("Export payload is not marked advisory-only.")
            if export_payload.get("read_only") is not True:
                warnings.append("Export payload is not marked read-only.")
            if export_payload.get("inventory_source_of_truth_preserved") is not True:
                warnings.append("Export payload does not preserve Inventory as source of truth.")

            response_payload = export_payload.get("response", {})
            dashboard_payload = response_payload.get("dashboard", {}) if isinstance(response_payload, dict) else {}
            summary_payload = dashboard_payload.get("summary", {}) if isinstance(dashboard_payload, dict) else {}
            total_count = summary_payload.get("total_count", 0) if isinstance(summary_payload, dict) else 0
            if isinstance(total_count, int) and manifest.record_count != total_count:
                warnings.append("Manifest record count does not match dashboard summary total count.")

        return DecisionReviewExportValidationResult(valid=not warnings, warnings=tuple(warnings))
