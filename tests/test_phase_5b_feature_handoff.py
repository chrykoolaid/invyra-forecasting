from invyra_forecasting.constants import Environment
from invyra_forecasting.intelligence.objects import (
    EvidenceLink,
    ForecastFeatureSet,
    ForecastIntelligence,
    SignalQualityAssessment,
    WeightedForecastSignal,
)
from invyra_forecasting.models.handoff import ForecastModelHandoffAdapter
from invyra_forecasting.models.service import ForecastModelService
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
        evidence_ref=f"evidence::{signal_id}",
        environment=Environment.TEST,
    )


def _intelligence() -> ForecastIntelligence:
    sale = _signal("S1", ForecastSignalType.SALE_EVENT, 12, "2026-07-01T00:00:00Z")
    stock = _signal(
        "S2",
        ForecastSignalType.LOCATION_STOCK_EVENT,
        60,
        "2026-07-01T01:00:00Z",
        ForecastSignalDirection.NEUTRAL,
    )
    quality = SignalQualityAssessment("S1", 1.0, 1.0, 1.0, 1.0)
    weighted = WeightedForecastSignal(sale, quality, 1.0)
    return ForecastIntelligence(
        item_id="ITEM-1",
        location_id="LOC-1",
        environment=Environment.TEST,
        analysis_window_days=30,
        normalized_signals=(sale, stock),
        quality_assessments=(quality,),
        weighted_signals=(weighted,),
        features=ForecastFeatureSet(
            item_id="ITEM-1",
            location_id="LOC-1",
            analysis_window_days=30,
            total_outbound_quantity=12,
            average_daily_outbound=0.4,
            latest_on_hand=60,
            signal_count=2,
            weighted_signal_count=1.0,
        ),
        evidence_links=(EvidenceLink("S1", "evidence::S1", "INVENTORY", "SALE_EVENT"),),
        confidence=0.95,
        audit_refs=("audit::forecast::1",),
    )


def test_handoff_includes_typed_engineered_features_without_changing_legacy_inputs():
    model_input = ForecastModelHandoffAdapter().from_intelligence(_intelligence())

    assert model_input.average_daily_demand == 0.4
    assert model_input.latest_on_hand == 60
    assert model_input.confidence == 0.95
    assert model_input.engineered_features
    assert model_input.feature_summary["engineered_feature_count"] == len(model_input.engineered_features)
    assert "rolling_7_day_demand" in model_input.feature_summary["engineered_feature_names"]


def test_model_input_serializes_engineered_features():
    model_input = ForecastModelHandoffAdapter().from_intelligence(_intelligence())
    payload = model_input.to_dict()

    assert payload["environment"] == "TEST"
    assert payload["engineered_features"]
    assert payload["engineered_features"][0]["category"]


def test_baseline_service_mentions_engineered_feature_context_and_remains_advisory():
    output = ForecastModelService().forecast(_intelligence(), forecast_days=30)

    assert output.advisory_only is True
    assert output.inventory_source_of_truth_preserved is True
    assert any("typed engineered feature" in line for line in output.explanation)
