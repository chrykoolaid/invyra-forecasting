from invyra_forecasting.constants import Environment
from invyra_forecasting.orchestration import AdvisoryForecastOrchestrator, AdvisoryForecastRequest
from invyra_forecasting.signals import (
    ForecastSignal,
    ForecastSignalDirection,
    ForecastSignalSource,
    ForecastSignalType,
    InMemoryForecastSignalRegistry,
    make_location_stock_signal,
)


def _sale_signal(quantity: float = 12) -> ForecastSignal:
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


def test_orchestrator_returns_end_to_end_advisory_forecast():
    registry = InMemoryForecastSignalRegistry()
    registry.publish(_sale_signal(quantity=12))
    registry.publish(
        make_location_stock_signal(
            item_id="ITEM-001",
            sku="SKU-1",
            location_id="LOC-001",
            on_hand=8,
            evidence_ref="SNAPSHOT-001",
            environment=Environment.TEST,
            confidence=0.9,
        )
    )

    response = AdvisoryForecastOrchestrator(registry).forecast(
        AdvisoryForecastRequest(
            item_id="ITEM-001",
            location_id="LOC-001",
            environment=Environment.TEST,
            analysis_window_days=30,
            forecast_days=14,
        )
    )

    assert response.item_id == "ITEM-001"
    assert response.location_id == "LOC-001"
    assert response.environment == Environment.TEST
    assert response.analysis_window_days == 30
    assert response.forecast_days == 14
    assert response.forecast_quantity > 0
    assert response.stockout_risk in {"HIGH", "MEDIUM", "LOW", "UNKNOWN"}
    assert response.confidence > 0
    assert response.evidence_refs
    assert response.intelligence_summary["signal_count"] == 2
    assert response.intelligence_summary["evidence_link_count"] == 2
    assert response.model_metadata["model_name"] == "baseline_explainable_demand_model"
    assert response.advisory_only is True
    assert response.inventory_source_of_truth_preserved is True


def test_orchestrator_does_not_mutate_signal_registry():
    registry = InMemoryForecastSignalRegistry()
    registry.publish(_sale_signal())
    orchestrator = AdvisoryForecastOrchestrator(registry)

    before_count = orchestrator.registered_signal_count()
    orchestrator.forecast(
        AdvisoryForecastRequest(
            item_id="ITEM-001",
            location_id="LOC-001",
            environment=Environment.TEST,
        )
    )
    after_count = orchestrator.registered_signal_count()

    assert before_count == 1
    assert after_count == 1


def test_orchestrator_empty_result_is_safe_and_explainable():
    registry = InMemoryForecastSignalRegistry()

    response = AdvisoryForecastOrchestrator(registry).forecast(
        AdvisoryForecastRequest(
            item_id="MISSING",
            location_id="LOC-001",
            environment=Environment.TEST,
        )
    )

    assert response.forecast_quantity == 0
    assert response.projected_days_of_cover is None
    assert response.stockout_risk == "UNKNOWN"
    assert response.confidence == 0
    assert response.evidence_refs == ()
    assert response.intelligence_summary["signal_count"] == 0
    assert response.advisory_only is True
    assert response.inventory_source_of_truth_preserved is True
    assert any("no evidence" in line.lower() for line in response.explanation)
