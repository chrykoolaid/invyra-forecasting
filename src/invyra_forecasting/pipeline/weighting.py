from __future__ import annotations

from invyra_forecasting.signals.schema import ForecastSignal, ForecastSignalType


DEFAULT_SIGNAL_WEIGHTS: dict[ForecastSignalType, float] = {
    ForecastSignalType.SALE_EVENT: 1.00,
    ForecastSignalType.STOCK_MOVEMENT: 0.85,
    ForecastSignalType.RECEIVING_EVENT: 0.80,
    ForecastSignalType.PURCHASE_ORDER_EVENT: 0.70,
    ForecastSignalType.SUPPLIER_LEAD_TIME: 0.90,
    ForecastSignalType.ADJUSTMENT_EVENT: 0.65,
    ForecastSignalType.WASTAGE_EVENT: 0.75,
    ForecastSignalType.MARKDOWN_EVENT: 0.70,
    ForecastSignalType.TRANSFER_EVENT: 0.70,
    ForecastSignalType.GAP_SCAN_EVENT: 0.60,
    ForecastSignalType.FLOOR_SCAN_EVENT: 0.60,
    ForecastSignalType.SHELF_EMPTY_EVENT: 0.65,
    ForecastSignalType.LOCATION_STOCK_EVENT: 0.75,
}


def weight_signal(signal: ForecastSignal, *, overrides: dict[ForecastSignalType, float] | None = None) -> float:
    """Return the advisory model weight for a signal type."""

    weights = DEFAULT_SIGNAL_WEIGHTS.copy()
    if overrides:
        weights.update(overrides)
    return max(0.0, min(1.0, weights.get(signal.signal_type, 0.50)))
