from __future__ import annotations

from invyra_forecasting.features.feature_contracts import ForecastFeature
from invyra_forecasting.features.feature_registry import FeatureRegistry, build_default_feature_registry
from invyra_forecasting.signals.schema import ForecastSignal


class FeatureEngineeringService:
    """Generates model-ready features from registered advisory signals.

    This service is intentionally read-only. It returns feature objects only and
    does not mutate inventory, write stock movements, create purchase orders, or
    approve purchase orders.
    """

    def __init__(self, registry: FeatureRegistry | None = None) -> None:
        self.registry = registry or build_default_feature_registry()

    def generate_features(
        self,
        signals: list[ForecastSignal] | tuple[ForecastSignal, ...],
        *,
        feature_names: list[str] | tuple[str, ...] | None = None,
    ) -> tuple[ForecastFeature, ...]:
        signal_tuple = tuple(signals)
        definitions = (
            tuple(self.registry.get(name) for name in feature_names)
            if feature_names is not None
            else self.registry.all()
        )
        return tuple(definition.builder(signal_tuple) for definition in definitions)

    def generate_feature_map(
        self,
        signals: list[ForecastSignal] | tuple[ForecastSignal, ...],
        *,
        feature_names: list[str] | tuple[str, ...] | None = None,
    ) -> dict[str, ForecastFeature]:
        return {feature.name: feature for feature in self.generate_features(signals, feature_names=feature_names)}
