from invyra_forecasting.features import (
    FeatureCategory,
    FeatureEngineeringService,
    FeatureRegistry,
    build_default_feature_registry,
)
from invyra_forecasting.features.demand_features import build_rolling_7_day_demand
from invyra_forecasting.features.feature_contracts import ForecastFeature
from invyra_forecasting.signals.schema import (
    ForecastSignal,
    ForecastSignalDirection,
    ForecastSignalSource,
    ForecastSignalType,
)


def _signal(
    signal_id: str,
    signal_type: ForecastSignalType,
    quantity: float,
    timestamp: str,
    direction: ForecastSignalDirection = ForecastSignalDirection.OUTBOUND,
    metadata: dict | None = None,
) -> ForecastSignal:
    return ForecastSignal.create(
        signal_id=signal_id,
        signal_type=signal_type,
        module_source=ForecastSignalSource.INVENTORY,
        item_id="ITEM-1",
        sku="SKU-1",
        location_id="LOC-1",
        quantity=quantity,
        unit="units",
        direction=direction,
        timestamp_utc=timestamp,
        metadata=metadata,
    )


def test_forecast_feature_object_creation_includes_metadata():
    feature = ForecastFeature(
        feature_id="DEMAND::example",
        name="example",
        category=FeatureCategory.DEMAND,
        value=10,
        unit="units",
        calculation_method="test_method",
        source_signal_ids=("S1",),
        data_window="P7D",
        metadata={"guardrail": "read_only"},
    )

    payload = feature.to_dict()

    assert payload["category"] == "DEMAND"
    assert payload["source_signal_ids"] == ["S1"]
    assert payload["metadata"] == {"guardrail": "read_only"}


def test_feature_registry_registration_and_duplicate_protection():
    registry = FeatureRegistry()
    definition = build_rolling_7_day_demand()

    registry.register(definition)

    assert registry.get("rolling_7_day_demand") is definition
    try:
        registry.register(definition)
    except ValueError as exc:
        assert "already registered" in str(exc)
    else:
        raise AssertionError("duplicate feature registration should fail")


def test_default_registry_contains_phase_5a_features():
    registry = build_default_feature_registry()

    assert "rolling_7_day_demand" in registry.names()
    assert "days_of_cover" in registry.names()
    assert "supplier_lead_time_average" in registry.names()
    assert "weekend_flag" in registry.names()


def test_rolling_demand_and_days_of_cover_generation():
    signals = [
        _signal("S1", ForecastSignalType.SALE_EVENT, 5, "2026-07-01T00:00:00Z"),
        _signal("S2", ForecastSignalType.SALE_EVENT, 7, "2026-07-02T00:00:00Z"),
        _signal(
            "S3",
            ForecastSignalType.LOCATION_STOCK_EVENT,
            24,
            "2026-07-02T01:00:00Z",
            ForecastSignalDirection.NEUTRAL,
        ),
    ]

    features = FeatureEngineeringService().generate_feature_map(
        signals,
        feature_names=("rolling_7_day_demand", "days_of_cover"),
    )

    assert features["rolling_7_day_demand"].value == 12
    assert features["days_of_cover"].value == 60


def test_missing_data_handling_is_safe_and_read_only():
    features = FeatureEngineeringService().generate_feature_map(
        [],
        feature_names=("rolling_7_day_demand", "days_of_cover", "supplier_lead_time_average"),
    )

    assert features["rolling_7_day_demand"].value == 0
    assert features["days_of_cover"].value is None
    assert features["supplier_lead_time_average"].value is None


def test_read_only_guardrail_preserved_by_feature_generation():
    signal = _signal("S1", ForecastSignalType.SALE_EVENT, 3, "2026-07-01T00:00:00Z")
    original_payload = signal.to_dict()

    FeatureEngineeringService().generate_features([signal])

    assert signal.to_dict() == original_payload
