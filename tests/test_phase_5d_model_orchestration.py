import pytest

from invyra_forecasting.constants import Environment
from invyra_forecasting.intelligence.objects import (
    EvidenceLink,
    ForecastFeatureSet,
    ForecastIntelligence,
    SignalQualityAssessment,
    WeightedForecastSignal,
)
from invyra_forecasting.models import (
    ForecastModelOrchestrator,
    ForecastModelRegistry,
    ModelLifecycleStatus,
    RegisteredForecastModel,
    build_default_model_registry,
)
from invyra_forecasting.models.baseline import BaselineExplainableDemandModel
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
    sale = _signal("S1", ForecastSignalType.SALE_EVENT, 15, "2026-07-01T00:00:00Z")
    quality = SignalQualityAssessment("S1", 1.0, 1.0, 1.0, 1.0)
    weighted = WeightedForecastSignal(sale, quality, 1.0)
    return ForecastIntelligence(
        item_id="ITEM-1",
        location_id="LOC-1",
        environment=Environment.TEST,
        analysis_window_days=30,
        normalized_signals=(sale,),
        quality_assessments=(quality,),
        weighted_signals=(weighted,),
        features=ForecastFeatureSet(
            item_id="ITEM-1",
            location_id="LOC-1",
            analysis_window_days=30,
            total_outbound_quantity=15,
            average_daily_outbound=0.5,
            latest_on_hand=10,
            signal_count=1,
            weighted_signal_count=1.0,
        ),
        evidence_links=(EvidenceLink("S1", "evidence::S1", "INVENTORY", "SALE_EVENT"),),
        confidence=0.92,
        audit_refs=("audit::1",),
    )


def test_default_model_registry_contains_production_baseline_model():
    registry = build_default_model_registry()
    eligible = registry.eligible(forecast_type="item_location_demand", forecast_days=30)

    assert len(eligible) == 1
    assert eligible[0].model_name == "baseline_explainable_demand_model"
    assert eligible[0].status == ModelLifecycleStatus.PRODUCTION


def test_model_registry_rejects_duplicate_model_id():
    registry = ForecastModelRegistry()
    baseline = BaselineExplainableDemandModel()
    model = RegisteredForecastModel(
        model_id="baseline::test",
        model_name=baseline.model_name,
        model_version=baseline.model_version,
        model=baseline,
        status=ModelLifecycleStatus.APPROVED,
    )

    registry.register(model)

    with pytest.raises(ValueError):
        registry.register(model)


def test_orchestrator_selects_eligible_model_with_explanation():
    selection = ForecastModelOrchestrator().select_model(forecast_type="item_location_demand", forecast_days=30)

    assert selection.selected_model.model_name == "baseline_explainable_demand_model"
    assert selection.selection_reasons
    assert selection.alternative_models_considered == ()


def test_orchestrator_forecast_preserves_advisory_guardrails():
    result = ForecastModelOrchestrator().forecast(_intelligence(), forecast_days=30)

    assert result.advisory_only is True
    assert result.inventory_source_of_truth_preserved is True
    assert result.model_output.forecast_quantity == 15
    assert result.selection.selected_model.model_name == "baseline_explainable_demand_model"
    assert result.orchestration_metadata["eligible_model_count"] == 1


def test_orchestrator_rejects_unsupported_horizon():
    with pytest.raises(ValueError):
        ForecastModelOrchestrator().select_model(forecast_type="item_location_demand", forecast_days=365)
