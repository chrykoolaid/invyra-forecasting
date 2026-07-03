from __future__ import annotations

from dataclasses import dataclass, field

from invyra_forecasting.constants import Environment
from invyra_forecasting.pipeline import assess_signal_quality, weight_signal
from invyra_forecasting.signals import ForecastSignal, ForecastSignalDirection, InMemoryForecastSignalRegistry


@dataclass(frozen=True)
class ForecastIntelligenceRequest:
    item_id: str
    location_id: str
    environment: Environment = Environment.TRAINING
    analysis_window_days: int = 30


@dataclass(frozen=True)
class ForecastSignalQuality:
    signal_id: str
    score: float
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class WeightedForecastSignal:
    signal: ForecastSignal
    quality_score: float
    weight: float
    weighted_score: float


@dataclass(frozen=True)
class ForecastEvidenceLink:
    signal_id: str
    evidence_ref: str
    module_source: str


@dataclass(frozen=True)
class ForecastFeatureSet:
    signal_count: int = 0
    latest_on_hand: float | None = None
    total_outbound_quantity: float = 0.0
    total_inbound_quantity: float = 0.0
    total_neutral_quantity: float = 0.0


@dataclass(frozen=True)
class ForecastIntelligenceResult:
    item_id: str
    location_id: str
    environment: Environment
    analysis_window_days: int
    normalized_signals: tuple[ForecastSignal, ...] = field(default_factory=tuple)
    quality_assessments: tuple[ForecastSignalQuality, ...] = field(default_factory=tuple)
    weighted_signals: tuple[WeightedForecastSignal, ...] = field(default_factory=tuple)
    features: ForecastFeatureSet = field(default_factory=ForecastFeatureSet)
    evidence_links: tuple[ForecastEvidenceLink, ...] = field(default_factory=tuple)
    audit_refs: tuple[str, ...] = field(default_factory=tuple)
    confidence: float = 0.0
    processing_metadata: dict[str, bool] = field(default_factory=dict)


class ForecastIntelligencePipeline:
    """Registry-backed Phase 2V intelligence pipeline.

    The pipeline reads normalized signals and produces model-ready advisory
    intelligence. It does not mutate inventory, stock movements, purchase
    orders, approvals, or ledger truth.
    """

    def __init__(self, registry: InMemoryForecastSignalRegistry) -> None:
        self.registry = registry

    def build(self, request: ForecastIntelligenceRequest) -> ForecastIntelligenceResult:
        signals = tuple(
            self.registry.list_signals(
                item_id=request.item_id,
                location_id=request.location_id,
                environment=request.environment,
            )
        )

        quality_assessments: list[ForecastSignalQuality] = []
        weighted_signals: list[WeightedForecastSignal] = []
        evidence_links: list[ForecastEvidenceLink] = []
        audit_refs: list[str] = []

        for signal in signals:
            quality = assess_signal_quality(signal)
            weight = weight_signal(signal)
            quality_assessments.append(
                ForecastSignalQuality(signal_id=signal.signal_id, score=quality.score, reasons=quality.reasons)
            )
            weighted_signals.append(
                WeightedForecastSignal(
                    signal=signal,
                    quality_score=quality.score,
                    weight=weight,
                    weighted_score=max(0.0, min(1.0, quality.score * weight)),
                )
            )
            if signal.evidence_ref:
                evidence_links.append(
                    ForecastEvidenceLink(
                        signal_id=signal.signal_id,
                        evidence_ref=signal.evidence_ref,
                        module_source=signal.module_source.value,
                    )
                )
                audit_refs.append(signal.evidence_ref)

        features = _build_feature_set(signals)
        confidence = _average([weighted.weighted_score for weighted in weighted_signals])

        return ForecastIntelligenceResult(
            item_id=request.item_id,
            location_id=request.location_id,
            environment=request.environment,
            analysis_window_days=request.analysis_window_days,
            normalized_signals=signals,
            quality_assessments=tuple(quality_assessments),
            weighted_signals=tuple(weighted_signals),
            features=features,
            evidence_links=tuple(evidence_links),
            audit_refs=tuple(dict.fromkeys(audit_refs)),
            confidence=confidence,
            processing_metadata={
                "advisory_only": True,
                "inventory_source_of_truth_preserved": True,
                "no_stock_mutation": True,
                "no_purchase_order_creation": True,
                "no_purchase_order_approval": True,
            },
        )


def _build_feature_set(signals: tuple[ForecastSignal, ...]) -> ForecastFeatureSet:
    latest_on_hand: float | None = None
    total_outbound = 0.0
    total_inbound = 0.0
    total_neutral = 0.0

    for signal in signals:
        if signal.metadata.get("on_hand") is not None:
            latest_on_hand = float(signal.metadata["on_hand"])
        if signal.direction == ForecastSignalDirection.OUTBOUND:
            total_outbound += signal.quantity
        elif signal.direction == ForecastSignalDirection.INBOUND:
            total_inbound += signal.quantity
        else:
            total_neutral += signal.quantity

    return ForecastFeatureSet(
        signal_count=len(signals),
        latest_on_hand=latest_on_hand,
        total_outbound_quantity=total_outbound,
        total_inbound_quantity=total_inbound,
        total_neutral_quantity=total_neutral,
    )


def _average(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)
