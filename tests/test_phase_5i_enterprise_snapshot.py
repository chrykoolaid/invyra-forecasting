import pytest

from invyra_forecasting.constants import Environment
from invyra_forecasting.enterprise import EnterpriseForecastSnapshot, EnterpriseForecastSnapshotService
from invyra_forecasting.intelligence.objects import (
    EvidenceLink,
    ForecastFeatureSet,
    ForecastIntelligence,
    SignalQualityAssessment,
    WeightedForecastSignal,
)
from invyra_forecasting.signals.schema import (
    ForecastSignal,
    ForecastSignalDirection,
    ForecastSignalSource,
    ForecastSignalType,
)


def _signal() -> ForecastSignal:
    return ForecastSignal.create(
        signal_id="S1",
        signal_type=ForecastSignalType.SALE_EVENT,
        module_source=ForecastSignalSource.INVENTORY,
        item_id="ITEM-1",
        sku="SKU-1",
        location_id="LOC-1",
        quantity=12,
        unit="units",
        direction=ForecastSignalDirection.OUTBOUND,
        timestamp_utc="2026-07-01T00:00:00Z",
        evidence_ref="evidence::S1",
        environment=Environment.TEST,
    )


def _intelligence() -> ForecastIntelligence:
    signal = _signal()
    quality = SignalQualityAssessment("S1", 0.9, 0.9, 0.9, 0.9)
    weighted = WeightedForecastSignal(signal, quality, 0.9)
    return ForecastIntelligence(
        item_id="ITEM-1",
        location_id="LOC-1",
        environment=Environment.TEST,
        analysis_window_days=30,
        normalized_signals=(signal,),
        quality_assessments=(quality,),
        weighted_signals=(weighted,),
        features=ForecastFeatureSet(
            item_id="ITEM-1",
            location_id="LOC-1",
            analysis_window_days=30,
            total_outbound_quantity=12,
            average_daily_outbound=0.4,
            latest_on_hand=24,
            signal_count=1,
            weighted_signal_count=0.9,
        ),
        evidence_links=(EvidenceLink("S1", "evidence::S1", "INVENTORY", "SALE_EVENT"),),
        confidence=0.9,
        audit_refs=("audit::1",),
    )


def test_enterprise_snapshot_builds_end_to_end_payload():
    snapshot = EnterpriseForecastSnapshotService().build(_intelligence(), forecast_days=30)
    payload = snapshot.to_dict()

    assert payload["metadata"]["phase"] == "5I"
    assert payload["metadata"]["evaluation_ready"] is True
    assert payload["orchestration_result"]["model_output"]["advisory_only"] is True
    assert payload["calibrated_confidence"]["advisory_only"] is True
    assert payload["evaluation_prediction"]["predicted_quantity"] == 12
    assert payload["lifecycle_entry"]["lifecycle_state"] == "PRODUCTION"
    assert payload["intelligence_v2"]["identity"]["item_id"] == "ITEM-1"


def test_enterprise_snapshot_preserves_guardrails():
    snapshot = EnterpriseForecastSnapshotService().build(_intelligence())

    assert snapshot.advisory_only is True
    assert snapshot.read_only is True
    assert snapshot.inventory_source_of_truth_preserved is True


def test_enterprise_snapshot_does_not_mutate_intelligence():
    intelligence = _intelligence()
    before = intelligence.to_dict()

    EnterpriseForecastSnapshotService().build(intelligence)

    assert intelligence.to_dict() == before


def test_enterprise_snapshot_rejects_guardrail_drift():
    snapshot = EnterpriseForecastSnapshotService().build(_intelligence())
    with pytest.raises(ValueError):
        EnterpriseForecastSnapshot(
            snapshot_id=snapshot.snapshot_id,
            generated_at_utc=snapshot.generated_at_utc,
            item_id=snapshot.item_id,
            location_id=snapshot.location_id,
            orchestration_result=snapshot.orchestration_result,
            calibrated_confidence=snapshot.calibrated_confidence,
            evaluation_prediction=snapshot.evaluation_prediction,
            lifecycle_entry=snapshot.lifecycle_entry,
            intelligence_v2=snapshot.intelligence_v2,
            read_only=False,
        )
