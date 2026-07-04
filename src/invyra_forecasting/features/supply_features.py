from __future__ import annotations

from statistics import pvariance

from invyra_forecasting.features.feature_contracts import FeatureCategory, FeatureDefinition, ForecastFeature
from invyra_forecasting.signals.schema import ForecastSignal, ForecastSignalType


def _lead_time_values(signals: tuple[ForecastSignal, ...]) -> tuple[float, ...]:
    values: list[float] = []
    for signal in signals:
        if signal.signal_type == ForecastSignalType.SUPPLIER_LEAD_TIME:
            value = signal.metadata.get("lead_time_days", signal.quantity)
            try:
                values.append(float(value))
            except (TypeError, ValueError):
                continue
    return tuple(values)


def _lead_time_source_ids(signals: tuple[ForecastSignal, ...]) -> tuple[str, ...]:
    return tuple(signal.signal_id for signal in signals if signal.signal_type == ForecastSignalType.SUPPLIER_LEAD_TIME)


def build_supplier_lead_time_average() -> FeatureDefinition:
    def builder(signals: tuple[ForecastSignal, ...]) -> ForecastFeature:
        values = _lead_time_values(signals)
        value = sum(values) / len(values) if values else None
        quality = min(1.0, len(values) / 3) if values else 0.5
        return ForecastFeature(
            feature_id="SUPPLY::supplier_lead_time_average",
            name="supplier_lead_time_average",
            category=FeatureCategory.SUPPLY,
            value=None if value is None else round(value, 4),
            unit="days",
            calculation_method="average_supplier_lead_time_days",
            source_signal_ids=_lead_time_source_ids(signals),
            data_window="available_supplier_lead_time_history",
            quality_score=quality,
            confidence_score=quality,
        )

    return FeatureDefinition("supplier_lead_time_average", FeatureCategory.SUPPLY, builder)


def build_supplier_lead_time_variance() -> FeatureDefinition:
    def builder(signals: tuple[ForecastSignal, ...]) -> ForecastFeature:
        values = _lead_time_values(signals)
        value = pvariance(values) if len(values) > 1 else 0.0
        quality = min(1.0, len(values) / 3) if values else 0.5
        return ForecastFeature(
            feature_id="SUPPLY::supplier_lead_time_variance",
            name="supplier_lead_time_variance",
            category=FeatureCategory.SUPPLY,
            value=round(value, 4),
            unit="days_squared",
            calculation_method="population_variance_supplier_lead_time_days",
            source_signal_ids=_lead_time_source_ids(signals),
            data_window="available_supplier_lead_time_history",
            quality_score=quality,
            confidence_score=quality,
        )

    return FeatureDefinition("supplier_lead_time_variance", FeatureCategory.SUPPLY, builder)
