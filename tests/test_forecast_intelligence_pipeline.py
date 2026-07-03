from invyra_forecasting.constants import Environment
from invyra_forecasting.intelligence import ForecastIntelligencePipeline, ForecastIntelligenceRequest
from invyra_forecasting.signals import (
    ForecastSignal,
    ForecastSignalDirection,
    ForecastSignalSource,
    ForecastSignalType,
    InMemoryForecastSignalRegistry,
    make_location_stock_signal,
)


def _sale_signal(quantity: float = 4) -> ForecastSignal:
    return ForecastSignal.create(
        signal_type=ForecastSignalType.SALE_EVENT,
        module_source=ForecastSignalSource.POS,
        item_id="ITEM-001",
        sku="SKU-1",
        location_id="LOC-001",
        quantity=quantity,
        unit="unit",
        direction=ForecastSignalDirection.OUTBOUND,
        reason_code="POS_SALE",
        confidence=0.95,
        evidence_ref="MOV-001",
        environment=Environment.TEST,
        timestamp_utc="2026-07-03T00:00:00Z",
        signal_id="SIG-MOV-001",
    )


def test_pipeline_builds_model_ready_intelligence_from_registered_signals():
    registry = InMemoryForecastSignalRegistry()
    registry.publish(_sale_signal(quantity=4))
    registry.publish(
        make_location_stock_signal(
            item_id="ITEM-001",
            sku="SKU-1",
            location_id="LOC-001",
            on_hand=18,
            evidence_ref="SNAPSHOT-001",
            environment=Environment.TEST,
            confidence=0.9,
        )
    )

    pipeline = ForecastIntelligencePipeline(registry)
    intelligence = pipeline.build(
        ForecastIntelligenceRequest(
            item_id="ITEM-001",
            location_id="LOC-001",
            environment=Environment.TEST,
            analysis_window_days=30,
        )
    )

    assert intelligence.item_id == "ITEM-001"
    assert intelligence.location_id == "LOC-001"
    assert intelligence.environment == Environment.TEST
    assert len(intelligence.normalized_signals) == 2
    assert len(intelligence.quality_assessments) == 2
    assert len(intelligence.weighted_signals) == 2
    assert intelligence.features.signal_count == 2
    assert intelligence.features.latest_on_hand == 18
    assert intelligence.features.total_outbound_quantity > 0
    assert intelligence.confidence > 0
    assert intelligence.processing_metadata["advisory_only"] is True
    assert intelligence.processing_metadata["inventory_source_of_truth_preserved"] is True


def test_pipeline_links_evidence_into_audit_refs():
    registry = InMemoryForecastSignalRegistry()
    registry.publish(_sale_signal())

    intelligence = ForecastIntelligencePipeline(registry).build(
        ForecastIntelligenceRequest(
            item_id="ITEM-001",
            location_id="LOC-001",
            environment=Environment.TEST,
        )
    )

    assert len(intelligence.evidence_links) == 1
    assert intelligence.evidence_links[0].evidence_ref == "MOV-001"
    assert intelligence.audit_refs == ("MOV-001",)


def test_pipeline_filters_by_environment_and_location():
    registry = InMemoryForecastSignalRegistry()
    registry.publish(_sale_signal())
    registry.publish(
        ForecastSignal.create(
            signal_type=ForecastSignalType.SALE_EVENT,
            module_source=ForecastSignalSource.POS,
            item_id="ITEM-001",
            sku="SKU-1",
            location_id="LOC-002",
            quantity=99,
            unit="unit",
            direction=ForecastSignalDirection.OUTBOUND,
            evidence_ref="MOV-OTHER-LOCATION",
            environment=Environment.TEST,
        )
    )
    registry.publish(
        ForecastSignal.create(
            signal_type=ForecastSignalType.SALE_EVENT,
            module_source=ForecastSignalSource.POS,
            item_id="ITEM-001",
            sku="SKU-1",
            location_id="LOC-001",
            quantity=99,
            unit="unit",
            direction=ForecastSignalDirection.OUTBOUND,
            evidence_ref="MOV-OTHER-ENV",
            environment=Environment.TRAINING,
        )
    )

    intelligence = ForecastIntelligencePipeline(registry).build(
        ForecastIntelligenceRequest(
            item_id="ITEM-001",
            location_id="LOC-001",
            environment=Environment.TEST,
        )
    )

    assert len(intelligence.normalized_signals) == 1
    assert intelligence.normalized_signals[0].evidence_ref == "MOV-001"


def test_empty_pipeline_result_is_safe_and_non_mutating():
    registry = InMemoryForecastSignalRegistry()

    intelligence = ForecastIntelligencePipeline(registry).build(
        ForecastIntelligenceRequest(
            item_id="MISSING",
            location_id="LOC-001",
            environment=Environment.TEST,
        )
    )

    assert intelligence.normalized_signals == ()
    assert intelligence.features.signal_count == 0
    assert intelligence.confidence == 0.0
    assert registry.count() == 0
