from invyra_forecasting.constants import Environment
from invyra_forecasting.intelligence import ForecastIntelligencePipeline, ForecastIntelligenceRequest
from invyra_forecasting.models import ForecastModelHandoffAdapter, ForecastModelService
from invyra_forecasting.signals import (
    ForecastSignal,
    ForecastSignalDirection,
    ForecastSignalSource,
    ForecastSignalType,
    InMemoryForecastSignalRegistry,
    make_location_stock_signal,
)


def _build_intelligence():
    registry = InMemoryForecastSignalRegistry()
    registry.publish(
        ForecastSignal.create(
            signal_type=ForecastSignalType.SALE_EVENT,
            module_source=ForecastSignalSource.POS,
            item_id="ITEM-001",
            sku="SKU-1",
            location_id="LOC-001",
            quantity=15,
            unit="unit",
            direction=ForecastSignalDirection.OUTBOUND,
            reason_code="POS_SALE",
            confidence=0.95,
            evidence_ref="MOV-001",
            environment=Environment.TEST,
            timestamp_utc="2026-07-03T00:00:00Z",
            signal_id="SIG-MOV-001",
        )
    )
    registry.publish(
        make_location_stock_signal(
            item_id="ITEM-001",
            sku="SKU-1",
            location_id="LOC-001",
            on_hand=6,
            evidence_ref="SNAPSHOT-001",
            environment=Environment.TEST,
            confidence=0.9,
        )
    )
    return ForecastIntelligencePipeline(registry).build(
        ForecastIntelligenceRequest(
            item_id="ITEM-001",
            location_id="LOC-001",
            environment=Environment.TEST,
            analysis_window_days=30,
        )
    )


def test_handoff_adapter_builds_stable_model_input_from_intelligence():
    intelligence = _build_intelligence()

    model_input = ForecastModelHandoffAdapter().from_intelligence(intelligence)

    assert model_input.item_id == "ITEM-001"
    assert model_input.location_id == "LOC-001"
    assert model_input.environment == Environment.TEST
    assert model_input.analysis_window_days == 30
    assert model_input.average_daily_demand > 0
    assert model_input.latest_on_hand == 6
    assert model_input.confidence == intelligence.confidence
    assert model_input.evidence_refs == intelligence.audit_refs
    assert model_input.feature_summary["signal_count"] == 2


def test_model_service_returns_advisory_explainable_forecast_output():
    intelligence = _build_intelligence()

    output = ForecastModelService().forecast(intelligence, forecast_days=14)

    assert output.item_id == "ITEM-001"
    assert output.location_id == "LOC-001"
    assert output.environment == Environment.TEST
    assert output.forecast_days == 14
    assert output.forecast_quantity > 0
    assert output.stockout_risk in {"HIGH", "MEDIUM", "LOW", "UNKNOWN"}
    assert output.confidence == intelligence.confidence
    assert output.evidence_refs == intelligence.audit_refs
    assert output.advisory_only is True
    assert output.inventory_source_of_truth_preserved is True
    assert output.model_name == "baseline_explainable_demand_model"
    assert any("Average daily demand" in line for line in output.explanation)
    assert any("evidence reference" in line for line in output.explanation)


def test_model_service_handles_no_demand_without_creating_operational_action():
    registry = InMemoryForecastSignalRegistry()
    intelligence = ForecastIntelligencePipeline(registry).build(
        ForecastIntelligenceRequest(
            item_id="ITEM-MISSING",
            location_id="LOC-001",
            environment=Environment.TEST,
        )
    )

    output = ForecastModelService().forecast(intelligence, forecast_days=14)

    assert output.forecast_quantity == 0
    assert output.projected_days_of_cover is None
    assert output.stockout_risk == "UNKNOWN"
    assert output.evidence_refs == ()
    assert output.advisory_only is True
    assert registry.count() == 0
