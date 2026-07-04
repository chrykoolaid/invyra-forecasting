import pytest

from invyra_forecasting.confidence import ConfidenceBand, ConfidenceCalibrationService, ConfidenceDimensionScores
from invyra_forecasting.constants import Environment
from invyra_forecasting.intelligence.objects import (
    EvidenceLink,
    ForecastFeatureSet,
    ForecastIntelligence,
    SignalQualityAssessment,
    WeightedForecastSignal,
)
from invyra_forecasting.models import ForecastModelOrchestrator
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


def _intelligence(*, confidence: float = 0.9, latest_on_hand: float | None = 30) -> ForecastIntelligence:
    sale = _signal("S1", ForecastSignalType.SALE_EVENT, 12, "2026-07-01T00:00:00Z")
    quality = SignalQualityAssessment("S1", confidence, confidence, confidence, confidence)
    weighted = WeightedForecastSignal(sale, quality, confidence)
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
            total_outbound_quantity=12,
            average_daily_outbound=0.4,
            latest_on_hand=latest_on_hand,
            signal_count=1,
            weighted_signal_count=confidence,
        ),
        evidence_links=(EvidenceLink("S1", "evidence::S1", "INVENTORY", "SALE_EVENT"),),
        confidence=confidence,
        audit_refs=("audit::1",),
    )


def test_confidence_dimension_scores_validate_range():
    with pytest.raises(ValueError):
        ConfidenceDimensionScores(
            data_confidence=1.2,
            feature_confidence=1.0,
            evidence_confidence=1.0,
            model_confidence=1.0,
            context_confidence=1.0,
            stability_confidence=1.0,
        )


def test_confidence_calibration_returns_explainable_advisory_result():
    intelligence = _intelligence()
    forecast_result = ForecastModelOrchestrator().forecast(intelligence, forecast_days=30)
    calibrated = ConfidenceCalibrationService().calibrate(intelligence, forecast_result)

    assert calibrated.advisory_only is True
    assert calibrated.inventory_source_of_truth_preserved is True
    assert calibrated.band in {ConfidenceBand.HIGH, ConfidenceBand.VERY_HIGH, ConfidenceBand.MODERATE}
    assert calibrated.positive_factors
    assert calibrated.calibration_metadata["selected_model"] == "baseline_explainable_demand_model"


def test_confidence_calibration_does_not_change_forecast_quantity():
    intelligence = _intelligence()
    forecast_result = ForecastModelOrchestrator().forecast(intelligence, forecast_days=30)
    before_quantity = forecast_result.model_output.forecast_quantity

    calibrated = ConfidenceCalibrationService().calibrate(intelligence, forecast_result)

    assert forecast_result.model_output.forecast_quantity == before_quantity
    assert calibrated.calibration_metadata["forecast_quantity_unchanged"] == before_quantity


def test_confidence_calibration_identifies_missing_context():
    intelligence = _intelligence(confidence=0.5, latest_on_hand=None)
    forecast_result = ForecastModelOrchestrator().forecast(intelligence, forecast_days=30)
    calibrated = ConfidenceCalibrationService().calibrate(intelligence, forecast_result)

    assert calibrated.band in {ConfidenceBand.LOW, ConfidenceBand.MODERATE}
    assert any("On-hand inventory context is unavailable" in factor for factor in calibrated.negative_factors)
    assert calibrated.improvement_guidance


def test_confidence_calibration_serializes_business_friendly_payload():
    intelligence = _intelligence()
    forecast_result = ForecastModelOrchestrator().forecast(intelligence, forecast_days=30)
    payload = ConfidenceCalibrationService().calibrate(intelligence, forecast_result).to_dict()

    assert "overall_confidence" in payload
    assert "band" in payload
    assert "dimensions" in payload
    assert payload["advisory_only"] is True
    assert payload["inventory_source_of_truth_preserved"] is True
