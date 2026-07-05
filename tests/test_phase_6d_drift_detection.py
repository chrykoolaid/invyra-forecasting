from __future__ import annotations

from dataclasses import replace

import pytest

from invyra_forecasting.evaluation import (
    DriftDetectionPolicy,
    DriftDetectionService,
    DriftSeverity,
    EvaluationPersistenceService,
    ForecastEvaluationService,
    ForecastOutcome,
    ForecastPrediction,
)


def _record(index: int, *, actual: float, predicted: float, confidence: float = 0.9):
    evaluator = ForecastEvaluationService()
    result = evaluator.evaluate(
        ForecastPrediction(
            forecast_id=f"forecast-{index}",
            item_id="item-1",
            location_id="location-1",
            model_name="baseline_explainable_demand_model",
            model_version="2W.1",
            forecast_horizon_days=30,
            predicted_quantity=predicted,
            confidence=confidence,
        ),
        ForecastOutcome(
            forecast_id=f"forecast-{index}",
            actual_quantity=actual,
        ),
    )
    service = EvaluationPersistenceService()
    return service.persist(
        result,
        evaluation_id=f"evaluation-{index}",
        metadata={"sequence": index},
    )


def test_phase_6d_reports_watch_when_history_is_insufficient() -> None:
    service = DriftDetectionService()

    report = service.detect((_record(1, actual=100.0, predicted=95.0),))

    assert report.severity == DriftSeverity.WATCH
    assert report.record_count == 1
    assert report.indicators[0].name == "insufficient_history"
    assert report.advisory_only is True
    assert report.read_only is True
    assert report.inventory_source_of_truth_preserved is True


def test_phase_6d_detects_warning_accuracy_drift() -> None:
    records = (
        _record(1, actual=100.0, predicted=98.0),
        _record(2, actual=100.0, predicted=97.0),
        _record(3, actual=100.0, predicted=75.0),
        _record(4, actual=100.0, predicted=74.0),
    )
    service = DriftDetectionService(
        DriftDetectionPolicy(
            minimum_records=4,
            recent_window_size=2,
            accuracy_drop_warning=0.12,
            accuracy_drop_critical=0.40,
        )
    )

    report = service.detect(records)

    assert report.severity == DriftSeverity.WARNING
    accuracy_indicator = next(indicator for indicator in report.indicators if indicator.name == "accuracy_drop")
    assert accuracy_indicator.severity == DriftSeverity.WARNING
    assert report.metadata["baseline_accuracy"] == 0.975
    assert report.metadata["recent_accuracy"] == 0.745


def test_phase_6d_detects_critical_accuracy_drift() -> None:
    records = (
        _record(1, actual=100.0, predicted=100.0),
        _record(2, actual=100.0, predicted=99.0),
        _record(3, actual=100.0, predicted=40.0),
        _record(4, actual=100.0, predicted=39.0),
    )
    service = DriftDetectionService(
        DriftDetectionPolicy(
            minimum_records=4,
            recent_window_size=2,
            accuracy_drop_critical=0.25,
        )
    )

    report = service.detect(records)

    assert report.severity == DriftSeverity.CRITICAL
    assert "retiring or replacing" in report.recommendation


def test_phase_6d_detects_calibration_warning() -> None:
    records = (
        _record(1, actual=100.0, predicted=95.0, confidence=0.95),
        _record(2, actual=100.0, predicted=96.0, confidence=0.95),
        _record(3, actual=100.0, predicted=99.0, confidence=0.10),
        _record(4, actual=100.0, predicted=98.0, confidence=0.10),
    )
    service = DriftDetectionService(
        DriftDetectionPolicy(
            minimum_records=4,
            recent_window_size=2,
            accuracy_drop_warning=0.50,
            calibration_gap_warning=0.20,
        )
    )

    report = service.detect(records)

    calibration_indicator = next(indicator for indicator in report.indicators if indicator.name == "calibration_gap")
    assert report.severity == DriftSeverity.WARNING
    assert calibration_indicator.severity == DriftSeverity.WARNING


def test_phase_6d_reports_none_when_model_is_stable() -> None:
    records = (
        _record(1, actual=100.0, predicted=96.0),
        _record(2, actual=100.0, predicted=97.0),
        _record(3, actual=100.0, predicted=96.5),
        _record(4, actual=100.0, predicted=97.5),
    )
    service = DriftDetectionService()

    report = service.detect(records)

    assert report.severity == DriftSeverity.NONE
    assert report.recommendation == "No drift action is recommended. Continue normal evaluation monitoring."


def test_phase_6d_rejects_non_advisory_report() -> None:
    report = DriftDetectionService().detect(
        (
            _record(1, actual=100.0, predicted=96.0),
            _record(2, actual=100.0, predicted=97.0),
            _record(3, actual=100.0, predicted=96.5),
            _record(4, actual=100.0, predicted=97.5),
        )
    )

    with pytest.raises(ValueError, match="drift reports must remain advisory-only"):
        replace(report, advisory_only=False)
