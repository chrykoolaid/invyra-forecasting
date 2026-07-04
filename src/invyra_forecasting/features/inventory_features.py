from __future__ import annotations

from invyra_forecasting.features.feature_contracts import FeatureCategory, FeatureDefinition, ForecastFeature
from invyra_forecasting.signals.schema import ForecastSignal, ForecastSignalDirection, ForecastSignalType


def _latest_on_hand(signals: tuple[ForecastSignal, ...]) -> ForecastSignal | None:
    stock_signals = [signal for signal in signals if signal.signal_type == ForecastSignalType.LOCATION_STOCK_EVENT]
    return max(stock_signals, key=lambda signal: signal.timestamp_utc, default=None)


def _rolling_30_day_demand(signals: tuple[ForecastSignal, ...]) -> float:
    outbound_sales = [
        signal
        for signal in signals
        if signal.signal_type == ForecastSignalType.SALE_EVENT and signal.direction == ForecastSignalDirection.OUTBOUND
    ]
    return sum(signal.quantity for signal in outbound_sales)


def build_days_of_cover() -> FeatureDefinition:
    def builder(signals: tuple[ForecastSignal, ...]) -> ForecastFeature:
        latest_stock = _latest_on_hand(signals)
        demand_30d = _rolling_30_day_demand(signals)
        average_daily_demand = demand_30d / 30 if demand_30d > 0 else 0.0
        value = None if latest_stock is None or average_daily_demand <= 0 else latest_stock.quantity / average_daily_demand
        quality = 1.0 if latest_stock is not None and demand_30d > 0 else 0.5
        source_ids = []
        if latest_stock is not None:
            source_ids.append(latest_stock.signal_id)
        source_ids.extend(
            signal.signal_id
            for signal in signals
            if signal.signal_type == ForecastSignalType.SALE_EVENT and signal.direction == ForecastSignalDirection.OUTBOUND
        )
        return ForecastFeature(
            feature_id="INVENTORY::days_of_cover",
            name="days_of_cover",
            category=FeatureCategory.INVENTORY,
            value=None if value is None else round(value, 4),
            unit="days",
            calculation_method="latest_on_hand_divided_by_average_daily_outbound_sales_30_days",
            source_signal_ids=tuple(source_ids),
            data_window="P30D",
            quality_score=quality,
            confidence_score=quality,
            metadata={"average_daily_demand": round(average_daily_demand, 4)},
        )

    return FeatureDefinition("days_of_cover", FeatureCategory.INVENTORY, builder)


def build_stockout_frequency() -> FeatureDefinition:
    def builder(signals: tuple[ForecastSignal, ...]) -> ForecastFeature:
        stockout_signals = tuple(
            signal
            for signal in signals
            if signal.signal_type in {ForecastSignalType.SHELF_EMPTY_EVENT, ForecastSignalType.GAP_SCAN_EVENT}
            or signal.metadata.get("stockout") is True
        )
        return ForecastFeature(
            feature_id="INVENTORY::stockout_frequency",
            name="stockout_frequency",
            category=FeatureCategory.INVENTORY,
            value=len(stockout_signals),
            unit="events",
            calculation_method="count_stockout_gap_and_shelf_empty_signals",
            source_signal_ids=tuple(signal.signal_id for signal in stockout_signals),
            data_window="P30D",
            quality_score=1.0,
            confidence_score=1.0 if stockout_signals else 0.75,
        )

    return FeatureDefinition("stockout_frequency", FeatureCategory.INVENTORY, builder)
