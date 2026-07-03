from __future__ import annotations

from collections.abc import Iterable

from invyra_forecasting.pipeline.evidence import build_evidence_chain
from invyra_forecasting.pipeline.features import extract_signal_features
from invyra_forecasting.pipeline.intelligence import ForecastIntelligenceObject
from invyra_forecasting.pipeline.quality import SignalQualityAssessment, assess_signal_quality
from invyra_forecasting.pipeline.weighting import weight_signal
from invyra_forecasting.signals.schema import ForecastSignal, ForecastSignalType


class ForecastSignalIngestionPipeline:
    """Converts normalized signals into forecast intelligence objects.

    This is the low-level signal-to-object pipeline. The registry-backed
    intelligence builder remains available from ``invyra_forecasting.intelligence``.
    The class is read-only and preserves the advisory forecasting boundary.
    """

    def __init__(self, *, weight_overrides: dict[ForecastSignalType, float] | None = None) -> None:
        self.weight_overrides = weight_overrides or {}

    def ingest(self, signal: ForecastSignal) -> ForecastIntelligenceObject:
        quality = assess_signal_quality(signal)
        weight = weight_signal(signal, overrides=self.weight_overrides)
        return build_forecast_intelligence_object(signal, quality, weight)

    def ingest_many(self, signals: Iterable[ForecastSignal]) -> list[ForecastIntelligenceObject]:
        return [self.ingest(signal) for signal in signals]


ForecastIntelligencePipeline = ForecastSignalIngestionPipeline


def build_forecast_intelligence_object(
    signal: ForecastSignal,
    quality: SignalQualityAssessment | None = None,
    weight: float | None = None,
) -> ForecastIntelligenceObject:
    quality = quality or assess_signal_quality(signal)
    signal_weight = weight_signal(signal) if weight is None else max(0.0, min(1.0, weight))
    weighted_score = max(0.0, min(1.0, quality.score * signal_weight))

    return ForecastIntelligenceObject(
        intelligence_id=f"FIO-{signal.signal_id}",
        source_signal_id=signal.signal_id,
        signal_type=signal.signal_type,
        module_source=signal.module_source,
        item_id=signal.item_id,
        sku=signal.sku,
        location_id=signal.location_id,
        timestamp_utc=signal.timestamp_utc,
        quantity=signal.quantity,
        unit=signal.unit,
        direction=signal.direction,
        quality_score=quality.score,
        weight=signal_weight,
        weighted_score=weighted_score,
        features=extract_signal_features(signal),
        evidence_chain=build_evidence_chain(signal),
        confidence=signal.confidence,
        reason_code=signal.reason_code,
        environment=signal.environment,
        metadata={"quality_reasons": quality.reasons, "source_metadata": signal.metadata},
    )
