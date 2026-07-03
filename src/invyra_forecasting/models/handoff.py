from __future__ import annotations

from invyra_forecasting.intelligence.objects import ForecastIntelligence
from invyra_forecasting.models.contracts import ForecastModelInput


class ForecastModelHandoffAdapter:
    """Converts ForecastIntelligence into a stable model input contract."""

    def from_intelligence(self, intelligence: ForecastIntelligence) -> ForecastModelInput:
        features = intelligence.features
        return ForecastModelInput(
            item_id=intelligence.item_id,
            location_id=intelligence.location_id,
            environment=intelligence.environment,
            analysis_window_days=intelligence.analysis_window_days,
            average_daily_demand=features.average_daily_outbound,
            latest_on_hand=features.latest_on_hand,
            confidence=intelligence.confidence,
            evidence_refs=intelligence.audit_refs,
            feature_summary={
                "signal_count": features.signal_count,
                "weighted_signal_count": features.weighted_signal_count,
                "total_outbound_quantity": features.total_outbound_quantity,
                "total_inbound_quantity": features.total_inbound_quantity,
                "net_quantity": features.net_quantity,
                "event_type_counts": dict(features.event_type_counts),
                "module_source_counts": dict(features.module_source_counts),
            },
        )
