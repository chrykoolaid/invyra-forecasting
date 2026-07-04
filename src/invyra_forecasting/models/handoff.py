from __future__ import annotations

from invyra_forecasting.features.feature_engineering_service import FeatureEngineeringService
from invyra_forecasting.features.feature_contracts import ForecastFeature
from invyra_forecasting.intelligence.objects import ForecastIntelligence
from invyra_forecasting.models.contracts import ForecastModelInput


class ForecastModelHandoffAdapter:
    """Converts ForecastIntelligence into a stable model input contract.

    Phase 5B enriches the handoff with typed engineered features while keeping
    the legacy baseline fields stable for backward compatibility.
    """

    def __init__(self, *, feature_service: FeatureEngineeringService | None = None) -> None:
        self._feature_service = feature_service or FeatureEngineeringService()

    def from_intelligence(self, intelligence: ForecastIntelligence) -> ForecastModelInput:
        features = intelligence.features
        engineered_features = self._generate_engineered_features(intelligence)
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
                "engineered_feature_count": len(engineered_features),
                "engineered_feature_names": [feature.name for feature in engineered_features],
            },
            engineered_features=engineered_features,
        )

    def _generate_engineered_features(self, intelligence: ForecastIntelligence) -> tuple[ForecastFeature, ...]:
        # Engineered features are generated from normalized advisory signals only.
        # This is a read-only handoff enrichment and does not mutate operational records.
        return self._feature_service.generate_features(intelligence.normalized_signals)
