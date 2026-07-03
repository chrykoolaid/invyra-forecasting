from invyra_forecasting.constants import Environment
from invyra_forecasting.intelligence import ForecastIntelligencePipeline, ForecastIntelligenceRequest
from invyra_forecasting.intelligence_summary import ForecastIntelligenceSummary, summarize_forecast_intelligence
from invyra_forecasting.signals import (
    ForecastSignal,
    ForecastSignalDirection,
    ForecastSignalSource,
    ForecastSignalType,
    InMemoryForecastSignalRegistry,
    make_location_stock_signal,
)


def _sale_signal() -> ForecastSignal:
    return ForecastSignal.create(
        signal_type=ForecastSignalType.SALE_EVENT,
        module_source=ForecastSignalSource.POS,
        item_id="ITEM-001",
        sku="SKU-1",
        location_id="LOC-001",
        quantity=3,
        unit="unit",
        direction=ForecastSignalDirection.OUTBOUND,
        reason_code="POS_SALE",
        confidence=0.9,
        evidence_ref="MOV-001",
        environment=Environment.TEST,
        timestamp_utc="2026-07-03T00:00:00Z",
        signal_id="SIG-MOV-001",
    )


def test_intelligence_summary_preserves_compact_context():
    registry = InMemoryForecastSignalRegistry()
    registry.publish(_sale_signal())
    registry.publish(
        make_location_stock_signal(
            item_id="ITEM-001",
            sku="SKU-1",
            location_id="LOC-001",
            on_hand=12,
            evidence_ref="SNAPSHOT-001",
            environment=Environment.TEST,
            confidence=0.8,
        )
    )

    intelligence = ForecastIntelligencePipeline(registry).build(
        ForecastIntelligenceRequest(item_id="ITEM-001", location_id="LOC-001", environment=Environment.TEST)
    )
    summary = summarize_forecast_intelligence(intelligence)

    assert isinstance(summary, ForecastIntelligenceSummary)
    assert summary.item_id == "ITEM-001"
    assert summary.location_id == "LOC-001"
    assert summary.environment == "TEST"
    assert summary.signal_count == len(intelligence.normalized_signals)
    assert set(summary.audit_refs) == set(intelligence.audit_refs)
    assert summary.feature_summary["latest_on_hand"] == intelligence.features.latest_on_hand
    assert summary.feature_summary["total_outbound_quantity"] == intelligence.features.total_outbound_quantity
    assert summary.governance["advisory_only"] is True
    assert summary.governance["source_of_truth_preserved"] is True


def test_empty_intelligence_summary_is_safe():
    registry = InMemoryForecastSignalRegistry()
    intelligence = ForecastIntelligencePipeline(registry).build(
        ForecastIntelligenceRequest(item_id="ITEM-404", location_id="LOC-001", environment=Environment.TEST)
    )

    summary = summarize_forecast_intelligence(intelligence)

    assert summary.signal_count == 0
    assert summary.confidence == 0.0
    assert summary.audit_refs == ()
    assert summary.quality_scores == ()
    assert summary.weighted_scores == ()
