from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

from invyra_forecasting.constants import Environment
from invyra_forecasting.signals.schema import ForecastSignal


@dataclass(frozen=True)
class SignalQualityAssessment:
    """Quality assessment for a normalized forecasting signal.

    Quality is an advisory confidence input. It does not mutate inventory,
    create stock movements, create purchase orders, or approve purchase orders.
    """

    signal_id: str
    score: float
    freshness_score: float
    completeness_score: float
    reliability_score: float
    issues: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class WeightedForecastSignal:
    """Signal plus its pipeline-calculated advisory weight."""

    signal: ForecastSignal
    quality: SignalQualityAssessment
    weight: float
    weight_reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal": self.signal.to_dict(),
            "quality": self.quality.to_dict(),
            "weight": self.weight,
            "weight_reasons": list(self.weight_reasons),
        }


@dataclass(frozen=True)
class ForecastFeatureSet:
    """Model-ready features extracted from advisory signals."""

    item_id: str
    location_id: str
    analysis_window_days: int
    total_outbound_quantity: float = 0.0
    total_inbound_quantity: float = 0.0
    net_quantity: float = 0.0
    average_daily_outbound: float = 0.0
    latest_on_hand: float | None = None
    signal_count: int = 0
    weighted_signal_count: float = 0.0
    event_type_counts: dict[str, int] = field(default_factory=dict)
    module_source_counts: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EvidenceLink:
    """Traceable evidence reference carried forward into forecast explanations."""

    signal_id: str
    evidence_ref: str
    module_source: str
    signal_type: str
    reason_code: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ForecastIntelligence:
    """Stable contract between registered signals and forecasting models.

    Forecast models consume this object instead of raw operational data. It is
    advisory-only and preserves Inventory as the source of truth.
    """

    item_id: str
    location_id: str
    environment: Environment
    analysis_window_days: int
    normalized_signals: tuple[ForecastSignal, ...]
    quality_assessments: tuple[SignalQualityAssessment, ...]
    weighted_signals: tuple[WeightedForecastSignal, ...]
    features: ForecastFeatureSet
    evidence_links: tuple[EvidenceLink, ...]
    confidence: float
    processing_metadata: dict[str, Any] = field(default_factory=dict)
    audit_refs: tuple[str, ...] = ()
    created_at_utc: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "location_id": self.location_id,
            "environment": self.environment.value,
            "analysis_window_days": self.analysis_window_days,
            "normalized_signals": [signal.to_dict() for signal in self.normalized_signals],
            "quality_assessments": [assessment.to_dict() for assessment in self.quality_assessments],
            "weighted_signals": [weighted.to_dict() for weighted in self.weighted_signals],
            "features": self.features.to_dict(),
            "evidence_links": [link.to_dict() for link in self.evidence_links],
            "confidence": self.confidence,
            "processing_metadata": dict(self.processing_metadata),
            "audit_refs": list(self.audit_refs),
            "created_at_utc": self.created_at_utc,
        }
