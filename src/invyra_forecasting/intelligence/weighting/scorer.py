from __future__ import annotations

from invyra_forecasting.intelligence.objects import SignalQualityAssessment, WeightedForecastSignal
from invyra_forecasting.signals.schema import ForecastSignal, ForecastSignalType


DEFAULT_TYPE_WEIGHTS: dict[ForecastSignalType, float] = {
    ForecastSignalType.SALE_EVENT: 1.0,
    ForecastSignalType.STOCK_MOVEMENT: 0.9,
    ForecastSignalType.RECEIVING_EVENT: 0.85,
    ForecastSignalType.PURCHASE_ORDER_EVENT: 0.75,
    ForecastSignalType.SUPPLIER_LEAD_TIME: 0.8,
    ForecastSignalType.ADJUSTMENT_EVENT: 0.65,
    ForecastSignalType.WASTAGE_EVENT: 0.7,
    ForecastSignalType.MARKDOWN_EVENT: 0.75,
    ForecastSignalType.TRANSFER_EVENT: 0.7,
    ForecastSignalType.GAP_SCAN_EVENT: 0.6,
    ForecastSignalType.FLOOR_SCAN_EVENT: 0.65,
    ForecastSignalType.SHELF_EMPTY_EVENT: 0.7,
    ForecastSignalType.LOCATION_STOCK_EVENT: 0.85,
}


class SignalWeightScorer:
    """Calculates advisory signal weights from quality and signal category."""

    def __init__(self, type_weights: dict[ForecastSignalType, float] | None = None) -> None:
        self._type_weights = type_weights or DEFAULT_TYPE_WEIGHTS

    def score(self, signal: ForecastSignal, quality: SignalQualityAssessment) -> WeightedForecastSignal:
        type_weight = self._type_weights.get(signal.signal_type, 0.5)
        weight = round(max(0.0, min(1.0, signal.confidence * quality.score * type_weight)), 4)
        reasons = (
            f"signal_confidence={signal.confidence:.2f}",
            f"quality_score={quality.score:.2f}",
            f"type_weight={type_weight:.2f}",
        )
        return WeightedForecastSignal(signal=signal, quality=quality, weight=weight, weight_reasons=reasons)

    def score_many(
        self,
        signals: list[ForecastSignal],
        quality_assessments: list[SignalQualityAssessment],
    ) -> list[WeightedForecastSignal]:
        quality_by_id = {assessment.signal_id: assessment for assessment in quality_assessments}
        return [self.score(signal, quality_by_id[signal.signal_id]) for signal in signals]
