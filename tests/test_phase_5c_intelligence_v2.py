import pytest

from invyra_forecasting.constants import Environment
from invyra_forecasting.intelligence import ForecastIntelligenceV2Builder
from invyra_forecasting.intelligence.objects import (
    EvidenceLink,
    ForecastFeatureSet,
    ForecastIntelligence,
    SignalQualityAssessment,
    WeightedForecastSignal,
)
from invyra_forecasting.intelligence.objects_v2 import ForecastConstraints, ForecastIntelligenceV2
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


def _v1_intelligence() -> ForecastIntelligence:
    sale = _signal("S1", ForecastSignalType.SALE_EVENT, 9, "2026-07-01T00:00:00Z")
    stock = _signal(
        "S2",
        ForecastSignalType.LOCATION_STOCK_EVENT,
        45,
        "2026-07-01T01:00:00Z",
        ForecastSignalDirection.NEUTRAL,
    )
    quality = SignalQualityAssessment("S1", 0.9, 0.9, 0.9, 0.9)
    weighted = WeightedForecastSignal(sale, quality, 0.9)
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
            total_outbound_quantity=9,
            average_daily_outbound=0.3,
            latest_on_hand=45,
            signal_count=2,
            weighted_signal_count=0.9,
        ),
        evidence_links=(EvidenceLink("S1", "evidence::S1", "INVENTORY", "SALE_EVENT"),),
        confidence=0.9,
        processing_metadata={"evidence_snapshot_id": "snapshot::1", "processing_time_ms": 12.5},
        audit_refs=("audit::1",),
    )


def test_v2_builder_preserves_identity_and_adds_engineered_features():
    v2 = ForecastIntelligenceV2Builder().from_v1(_v1_intelligence(), forecast_horizon_days=30)

    assert isinstance(v2, ForecastIntelligenceV2)
    assert v2.identity.item_id == "ITEM-1"
    assert v2.identity.location_id == "LOC-1"
    assert v2.identity.environment == Environment.TEST
    assert v2.identity.forecast_horizon_days == 30
    assert v2.engineered_features
    assert v2.created_from_version == "ForecastIntelligenceV1"


def test_v2_serialization_contains_required_enterprise_packages():
    payload = ForecastIntelligenceV2Builder().from_v1(_v1_intelligence()).to_dict()

    assert payload["identity"]["environment"] == "TEST"
    assert payload["context"]["current_inventory"]["latest_on_hand"] == 45
    assert payload["engineered_features"]
    assert payload["evidence_package"][0]["evidence_ref"] == "evidence::S1"
    assert payload["confidence_package"]["overall_confidence"] == 0.9
    assert payload["quality_assessment"]["signal_completeness"] == "available"
    assert payload["forecast_constraints"]["advisory_only"] is True
    assert payload["governance_metadata"]["feature_version"] == "5A"
    assert payload["audit_metadata"]["evidence_snapshot_id"] == "snapshot::1"


def test_v2_constraints_reject_operational_mutation():
    with pytest.raises(ValueError):
        ForecastConstraints(may_modify_inventory=True).assert_guardrails()
    with pytest.raises(ValueError):
        ForecastConstraints(may_create_purchase_orders=True).assert_guardrails()
    with pytest.raises(ValueError):
        ForecastConstraints(may_override_ledger_truth=True).assert_guardrails()


def test_v2_builder_does_not_mutate_v1_intelligence():
    v1 = _v1_intelligence()
    before = v1.to_dict()

    ForecastIntelligenceV2Builder().from_v1(v1)

    assert v1.to_dict() == before
