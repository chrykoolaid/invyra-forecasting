from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from invyra_forecasting.intelligence import ForecastIntelligenceResult


@dataclass(frozen=True)
class ForecastIntelligenceSummary:
    """Compact summary of forecast intelligence context."""

    item_id: str
    location_id: str
    environment: str
    signal_count: int
    confidence: float
    audit_refs: tuple[str, ...] = field(default_factory=tuple)
    quality_scores: tuple[float, ...] = field(default_factory=tuple)
    weighted_scores: tuple[float, ...] = field(default_factory=tuple)
    feature_summary: dict[str, Any] = field(default_factory=dict)
    governance: dict[str, bool] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def summarize_forecast_intelligence(intelligence: ForecastIntelligenceResult) -> ForecastIntelligenceSummary:
    """Create a stable summary from a registry-backed intelligence result."""

    return ForecastIntelligenceSummary(
        item_id=intelligence.item_id,
        location_id=intelligence.location_id,
        environment=intelligence.environment.value,
        signal_count=intelligence.features.signal_count,
        confidence=intelligence.confidence,
        audit_refs=intelligence.audit_refs,
        quality_scores=tuple(assessment.score for assessment in intelligence.quality_assessments),
        weighted_scores=tuple(weighted.weighted_score for weighted in intelligence.weighted_signals),
        feature_summary={
            "latest_on_hand": intelligence.features.latest_on_hand,
            "total_outbound_quantity": intelligence.features.total_outbound_quantity,
            "total_inbound_quantity": intelligence.features.total_inbound_quantity,
            "total_neutral_quantity": intelligence.features.total_neutral_quantity,
        },
        governance={
            "advisory_only": intelligence.processing_metadata.get("advisory_only", False),
            "source_of_truth_preserved": intelligence.processing_metadata.get(
                "inventory_source_of_truth_preserved", False
            ),
        },
    )
