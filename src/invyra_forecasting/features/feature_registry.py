from __future__ import annotations

from invyra_forecasting.features.feature_contracts import FeatureDefinition
from invyra_forecasting.features.demand_features import (
    build_demand_trend,
    build_demand_volatility,
    build_rolling_7_day_demand,
    build_rolling_30_day_demand,
)
from invyra_forecasting.features.inventory_features import build_days_of_cover, build_stockout_frequency
from invyra_forecasting.features.supply_features import (
    build_supplier_lead_time_average,
    build_supplier_lead_time_variance,
)
from invyra_forecasting.features.time_features import build_day_of_week, build_month, build_weekend_flag


class FeatureRegistry:
    """Central registry of feature definitions.

    The registry controls which feature builders are eligible for advisory
    feature generation. It does not perform operational writes.
    """

    def __init__(self) -> None:
        self._definitions: dict[str, FeatureDefinition] = {}

    def register(self, definition: FeatureDefinition) -> None:
        if definition.name in self._definitions:
            raise ValueError(f"Feature definition already registered: {definition.name}")
        self._definitions[definition.name] = definition

    def get(self, name: str) -> FeatureDefinition:
        try:
            return self._definitions[name]
        except KeyError as exc:
            raise KeyError(f"Unknown feature definition: {name}") from exc

    def all(self) -> tuple[FeatureDefinition, ...]:
        return tuple(self._definitions.values())

    def names(self) -> tuple[str, ...]:
        return tuple(self._definitions.keys())


def build_default_feature_registry() -> FeatureRegistry:
    registry = FeatureRegistry()
    for definition in (
        build_rolling_7_day_demand(),
        build_rolling_30_day_demand(),
        build_demand_trend(),
        build_demand_volatility(),
        build_days_of_cover(),
        build_stockout_frequency(),
        build_supplier_lead_time_average(),
        build_supplier_lead_time_variance(),
        build_day_of_week(),
        build_month(),
        build_weekend_flag(),
    ):
        registry.register(definition)
    return registry
