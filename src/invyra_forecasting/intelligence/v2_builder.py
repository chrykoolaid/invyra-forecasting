from __future__ import annotations

from invyra_forecasting.features.feature_engineering_service import FeatureEngineeringService
from invyra_forecasting.intelligence.objects import ForecastIntelligence
from invyra_forecasting.intelligence.objects_v2 import ForecastIntelligenceV2


class ForecastIntelligenceV2Builder:
    """Builds ForecastIntelligenceV2 from the stable V1 intelligence contract.

    The builder enriches V1 intelligence with Phase 5A engineered features while
    preserving the original V1 object and all advisory-only guardrails.
    """

    def __init__(self, *, feature_service: FeatureEngineeringService | None = None) -> None:
        self._feature_service = feature_service or FeatureEngineeringService()

    def from_v1(
        self,
        intelligence: ForecastIntelligence,
        *,
        forecast_horizon_days: int | None = None,
    ) -> ForecastIntelligenceV2:
        engineered_features = self._feature_service.generate_features(intelligence.normalized_signals)
        return ForecastIntelligenceV2.from_v1(
            intelligence,
            engineered_features=engineered_features,
            forecast_horizon_days=forecast_horizon_days,
        )
