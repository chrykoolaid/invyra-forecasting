from __future__ import annotations

from datetime import datetime, timedelta
from statistics import pstdev

from invyra_forecasting.features.feature_contracts import FeatureCategory, FeatureDefinition, ForecastFeature
from invyra_forecasting.signals.schema import ForecastSignal, ForecastSignalDirection, ForecastSignalType


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _anchor_timestamp(signals: tuple[ForecastSignal, ...]) -> datetime | None:
    timestamps = [_parse_timestamp(signal.timestamp_utc) for signal in signals]
    return max(timestamps, default=None)


def _outbound_sales(signals: tuple[ForecastSignal, ...], *, days: int | None = None) -> tuple[ForecastSignal, ...]:
    anchor = _anchor_timestamp(signals)
    if anchor is None:
        return ()
    start = anchor - timedelta(days=(days - 1)) if days else None
    selected: list[ForecastSignal] = []
    for signal in signals:
        timestamp = _parse_timestamp(signal.timestamp_utc)
        if signal.signal_type == ForecastSignalType.SALE_EVENT and signal.direction == ForecastSignalDirection.OUTBOUND:
            if start is None or start <= timestamp <= anchor:
                selected.append(signal)
    return tuple(selected)


def _daily_quantities(signals: tuple[ForecastSignal, ...], *, days: int) -> list[float]:
    anchor = _anchor_timestamp(signals)
    if anchor is None:
        return [0.0] * days
    buckets = {(anchor.date() - timedelta(days=offset)): 0.0 for offset in range(days)}
    for signal in _outbound_sales(signals, days=days):
        buckets[_parse_timestamp(signal.timestamp_utc).date()] += signal.quantity
    ordered_days = [anchor.date() - timedelta(days=offset) for offset in reversed(range(days))]
    return [buckets[day] for day in ordered_days]


def _feature(
    *,
    name: str,
    value: float,
    source_signals: tuple[ForecastSignal, ...],
    method: str,
    data_window: str,
    metadata: dict[str, object] | None = None,
) -> ForecastFeature:
    completeness = min(1.0, len(source_signals) / 3) if source_signals else 0.5
    confidence = round(min(1.0, max(0.0, completeness)), 4)
    return ForecastFeature(
        feature_id=f"DEMAND::{name}",
        name=name,
        category=FeatureCategory.DEMAND,
        value=round(value, 4),
        unit="units",
        calculation_method=method,
        source_signal_ids=tuple(signal.signal_id for signal in source_signals),
        data_window=data_window,
        quality_score=confidence,
        confidence_score=confidence,
        metadata=metadata or {},
    )


def build_rolling_7_day_demand() -> FeatureDefinition:
    def builder(signals: tuple[ForecastSignal, ...]) -> ForecastFeature:
        source_signals = _outbound_sales(signals, days=7)
        return _feature(
            name="rolling_7_day_demand",
            value=sum(signal.quantity for signal in source_signals),
            source_signals=source_signals,
            method="sum_outbound_sale_event_quantity_7_days",
            data_window="P7D",
        )

    return FeatureDefinition("rolling_7_day_demand", FeatureCategory.DEMAND, builder)


def build_rolling_30_day_demand() -> FeatureDefinition:
    def builder(signals: tuple[ForecastSignal, ...]) -> ForecastFeature:
        source_signals = _outbound_sales(signals, days=30)
        return _feature(
            name="rolling_30_day_demand",
            value=sum(signal.quantity for signal in source_signals),
            source_signals=source_signals,
            method="sum_outbound_sale_event_quantity_30_days",
            data_window="P30D",
        )

    return FeatureDefinition("rolling_30_day_demand", FeatureCategory.DEMAND, builder)


def build_demand_trend() -> FeatureDefinition:
    def builder(signals: tuple[ForecastSignal, ...]) -> ForecastFeature:
        daily = _daily_quantities(signals, days=30)
        first_half = daily[:15]
        second_half = daily[15:]
        first_average = sum(first_half) / len(first_half)
        second_average = sum(second_half) / len(second_half)
        trend = 0.0 if first_average == 0 and second_average == 0 else second_average - first_average
        return _feature(
            name="demand_trend",
            value=trend,
            source_signals=_outbound_sales(signals, days=30),
            method="second_15_day_average_minus_first_15_day_average",
            data_window="P30D",
            metadata={"first_half_average": round(first_average, 4), "second_half_average": round(second_average, 4)},
        )

    return FeatureDefinition("demand_trend", FeatureCategory.DEMAND, builder)


def build_demand_volatility() -> FeatureDefinition:
    def builder(signals: tuple[ForecastSignal, ...]) -> ForecastFeature:
        daily = _daily_quantities(signals, days=30)
        volatility = pstdev(daily) if len(daily) > 1 else 0.0
        return _feature(
            name="demand_volatility",
            value=volatility,
            source_signals=_outbound_sales(signals, days=30),
            method="population_standard_deviation_daily_demand_30_days",
            data_window="P30D",
        )

    return FeatureDefinition("demand_volatility", FeatureCategory.DEMAND, builder)
