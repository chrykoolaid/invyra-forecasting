from __future__ import annotations

from invyra_forecasting.intelligence.objects import ForecastFeatureSet, WeightedForecastSignal
from invyra_forecasting.signals.schema import ForecastSignalDirection, ForecastSignalType


class ForecastFeatureExtractor:
    """Extracts model-ready, explainable features from weighted signals."""

    def extract(
        self,
        weighted_signals: list[WeightedForecastSignal],
        *,
        item_id: str,
        location_id: str,
        analysis_window_days: int = 30,
    ) -> ForecastFeatureSet:
        total_outbound = 0.0
        total_inbound = 0.0
        latest_on_hand: float | None = None
        event_type_counts: dict[str, int] = {}
        module_source_counts: dict[str, int] = {}

        for weighted in weighted_signals:
            signal = weighted.signal
            event_type_counts[signal.signal_type.value] = event_type_counts.get(signal.signal_type.value, 0) + 1
            module_source_counts[signal.module_source.value] = module_source_counts.get(signal.module_source.value, 0) + 1

            weighted_quantity = signal.quantity * weighted.weight
            if signal.direction == ForecastSignalDirection.OUTBOUND:
                total_outbound += weighted_quantity
            elif signal.direction == ForecastSignalDirection.INBOUND:
                total_inbound += weighted_quantity
            elif signal.signal_type == ForecastSignalType.LOCATION_STOCK_EVENT:
                latest_on_hand = signal.quantity

        net_quantity = total_inbound - total_outbound
        average_daily_outbound = total_outbound / max(analysis_window_days, 1)
        weighted_signal_count = sum(weighted.weight for weighted in weighted_signals)

        return ForecastFeatureSet(
            item_id=item_id,
            location_id=location_id,
            analysis_window_days=analysis_window_days,
            total_outbound_quantity=round(total_outbound, 4),
            total_inbound_quantity=round(total_inbound, 4),
            net_quantity=round(net_quantity, 4),
            average_daily_outbound=round(average_daily_outbound, 4),
            latest_on_hand=latest_on_hand,
            signal_count=len(weighted_signals),
            weighted_signal_count=round(weighted_signal_count, 4),
            event_type_counts=event_type_counts,
            module_source_counts=module_source_counts,
        )
