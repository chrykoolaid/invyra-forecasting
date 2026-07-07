from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from invyra_forecasting.decision_review_export import DecisionReviewExportProjection
from invyra_forecasting.decision_review_export_manifest import (
    DecisionReviewExportManifest,
    DecisionReviewExportManifestBuilder,
)
from invyra_forecasting.decision_review_export_validation import (
    DecisionReviewExportManifestValidator,
    DecisionReviewExportValidationResult,
)


@dataclass(frozen=True)
class DecisionReviewExportBundle:
    """Read-only completed export bundle for forecast decision review payloads."""

    export: DecisionReviewExportProjection
    manifest: DecisionReviewExportManifest
    validation: DecisionReviewExportValidationResult
    bundle_version: str = "8L.1"
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def ready_for_delivery(self) -> bool:
        return self.validation.valid

    def to_dict(self) -> dict[str, Any]:
        return {
            "bundle_version": self.bundle_version,
            "ready_for_delivery": self.ready_for_delivery,
            "export": self.export.to_dict(),
            "manifest": self.manifest.to_dict(),
            "validation": self.validation.to_dict(),
            "generated_at": self.generated_at,
            "advisory_only": True,
            "read_only": True,
            "inventory_source_of_truth_preserved": True,
        }


class DecisionReviewExportBundleBuilder:
    """Builds complete read-only export bundles without writing or transmitting data."""

    def __init__(
        self,
        *,
        manifest_builder: DecisionReviewExportManifestBuilder | None = None,
        validator: DecisionReviewExportManifestValidator | None = None,
    ) -> None:
        self._manifest_builder = manifest_builder or DecisionReviewExportManifestBuilder()
        self._validator = validator or DecisionReviewExportManifestValidator()

    def build(self, export: DecisionReviewExportProjection) -> DecisionReviewExportBundle:
        manifest = self._manifest_builder.build(export)
        validation = self._validator.validate(manifest)
        return DecisionReviewExportBundle(export=export, manifest=manifest, validation=validation)
