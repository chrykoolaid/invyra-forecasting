from __future__ import annotations

from datetime import UTC, datetime

from invyra_forecasting.features.feature_contracts import FeatureCategory, FeatureDefinition, ForecastFeature
from invyra_forecasting.signals.schema import ForecastSignal


def _anchor(signals: tuple[ForecastSignal, ...]) -> datetime:
    timestamps = [datetime.fromisoformat(signal.timestamp_utc.replace("Z", "+00:00")) for signal in signals]
    return max(timestamps, default=datetime.now(UTC))


def build_day_of_week() -> FeatureDefinition:
    def builder(signals: tuple[ForecastSignal, ...]) -> ForecastFeature:
        anchor = _anchor(signals)
        return ForecastFeature(
            feature_id="TIME::day_of_week",
            name="day_of_week",
            category=FeatureCategory.TIME,
            value=anchor.weekday(),
            unit="weekday_index",
            calculation_method="anchor_timestamp_weekday_monday_zero",
            source_signal_ids=tuple(signal.signal_id for signal in signals),
            data_window="anchor_timestamp",
            quality_score=1.0,
            confidence_score=1.0,
            metadata={"anchor_timestamp_utc": anchor.isoformat(timespec="seconds").replace("+00:00", "Z")},
        )

    return FeatureDefinition("day_of_week", FeatureCategory.TIME, builder)


def build_month() -> FeatureDefinition:
    def builder(signals: tuple[ForecastSignal, ...]) -> ForecastFeature:
        anchor = _anchor(signals)
        return ForecastFeature(
            feature_id="TIME::month",
            name="month",
            category=FeatureCategory.TIME,
            value=anchor.month,
            unit="month_number",
            calculation_method="anchor_timestamp_month",
            source_signal_ids=tuple(signal.signal_id for signal in signals),
            data_window="anchor_timestamp",
            quality_score=1.0,
            confidence_score=1.0,
            metadata={"anchor_timestamp_utc": anchor.isoformat(timespec="seconds").replace("+00:00", "Z")},
        )

    return FeatureDefinition("month", FeatureCategory.TIME, builder)


def build_weekend_flag() -> FeatureDefinition:
    def builder(signals: tuple[ForecastSignal, ...]) -> ForecastFeature:
        anchor = _anchor(signals)
        return ForecastFeature(
            feature_id="TIME::weekend_flag",
            name="weekend_flag",
            category=FeatureCategory.TIME,
            value=anchor.weekday() >= 5,
            unit=None,
            calculation_method="anchor_timestamp_weekday_is_saturday_or_sunday",
            source_signal_ids=tuple(signal.signal_id for signal in signals),
            data_window="anchor_timestamp",
            quality_score=1.0,
            confidence_score=1.0,
            metadata={"anchor_timestamp_utc": anchor.isoformat(timespec="seconds").replace("+00:00", "Z")},
        )

    return FeatureDefinition("weekend_flag", FeatureCategory.TIME, builder)
