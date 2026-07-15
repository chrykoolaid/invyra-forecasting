from __future__ import annotations

import pytest

from invyra_forecasting.evaluation.metrics import ForecastEvaluationResult
from invyra_forecasting.evaluation.persistence import ForecastEvaluationRecord
from invyra_forecasting.evaluation_evidence_persistence import (
    EvaluationEvidenceRecord,
    EvaluationEvidenceStage,
)
from invyra_forecasting.model_performance_registry import (
    ModelLifecycleStatus,
    ModelPerformanceRegistryEntry,
)
from invyra_forecasting.model_performance_statistics import (
    ModelPerformanceStatisticsService,
)


def _registry() -> ModelPerformanceRegistryEntry:
    return ModelPerformanceRegistryEntry(
        registry_id="registry-1",
        model_name="seasonal-naive",
        model_version="1.0",
        lifecycle_status=ModelLifecycleStatus.ACTIVE,
        supported_forecast_horizons=(7, 14),
        supported_demand_profiles=("seasonal",),
        namespace="default",
        registered_at_utc="2026-07-15T16:00:00+00:00",
    )


def _evaluation(evaluation_id: str, *, horizon: int = 7, absolute_error: float = 2.0) -> ForecastEvaluationRecord:
    result = ForecastEvaluationResult(
        forecast_id=f"forecast-{evaluation_id}",
        item_id="item-1",
        location_id="location-1",
        model_name="seasonal-naive",
        model_version="1.0",
        predicted_quantity=10.0,
        actual_quantity=12.0,
        forecast_error=2.0,
        absolute_error=absolute_error,
        squared_error=absolute_error**2,
        absolute_percentage_error=absolute_error / 12.0,
        bias=2.0,
        accuracy_score=0.8,
        confidence=0.7,
        calibration_gap=0.1,
        evaluation_metadata={"forecast_horizon_days": horizon},
    )
    return ForecastEvaluationRecord(evaluation_id=evaluation_id, result=result)


def _evidence(evaluation_id: str, *, horizon: int = 7, eligible: bool = True) -> EvaluationEvidenceRecord:
    forecast_id = f"forecast-{evaluation_id}"
    guardrails = {
        "advisory_only": True,
        "read_only": True,
        "inventory_source_of_truth_preserved": True,
    }
    return EvaluationEvidenceRecord(
        record_id=f"record-{evaluation_id}",
        evaluation_id=evaluation_id,
        history_id=f"history-{evaluation_id}",
        forecast_id=forecast_id,
        outcome_evidence_id=f"outcome-{evaluation_id}",
        stage=EvaluationEvidenceStage.FINAL if eligible else EvaluationEvidenceStage.PARTIAL,
        linkage={
            "evaluation_id": evaluation_id,
            "history_id": f"history-{evaluation_id}",
            "forecast_id": forecast_id,
            "item_id": "item-1",
            "location_id": "location-1",
            "model_name": "seasonal-naive",
            "model_version": "1.0",
            "forecast_horizon_days": horizon,
            **guardrails,
        },
        window_assessment={"final_evaluation_eligible": eligible, **guardrails},
        actual_outcome={
            "forecast_id": forecast_id,
            "outcome_evidence_id": f"outcome-{evaluation_id}",
            "item_id": "item-1",
            "location_id": "location-1",
            "data_completeness": 1.0 if eligible else 0.5,
            "evidence_refs": ["inventory-ledger-ref"],
            **guardrails,
        },
        censoring_assessment={
            "forecast_id": forecast_id,
            "outcome_evidence_id": f"outcome-{evaluation_id}",
            "item_id": "item-1",
            "location_id": "location-1",
            "status": "uncensored",
            "ranking_evidence_eligible": eligible,
            **guardrails,
        },
        namespace="default",
    )


def test_aggregates_only_e7_certified_evidence() -> None:
    service = ModelPerformanceStatisticsService()
    first = _evaluation("eval-1", absolute_error=2.0)
    second = _evaluation("eval-2", absolute_error=4.0)
    ignored = _evaluation("eval-3", absolute_error=100.0)

    stats = service.summarize(
        _registry(),
        (_evidence("eval-1"), _evidence("eval-2"), _evidence("eval-3", eligible=False)),
        (first, second, ignored),
    )

    assert stats.eligible_evaluation_count == 2
    assert stats.mae == 3.0
    assert stats.rmse == 3.1623
    assert stats.bias == 2.0
    assert stats.average_accuracy_score == 0.8
    assert stats.average_calibration_gap == 0.1


def test_supports_horizon_specific_statistics() -> None:
    stats = ModelPerformanceStatisticsService().summarize(
        _registry(),
        (_evidence("eval-7", horizon=7), _evidence("eval-14", horizon=14)),
        (_evaluation("eval-7", horizon=7), _evaluation("eval-14", horizon=14)),
        forecast_horizon_days=14,
    )

    assert stats.forecast_horizon_days == 14
    assert stats.eligible_evaluation_count == 1


def test_returns_empty_statistics_when_no_certified_evidence_exists() -> None:
    stats = ModelPerformanceStatisticsService().summarize(
        _registry(),
        (_evidence("eval-1", eligible=False),),
        (_evaluation("eval-1"),),
    )

    assert stats.eligible_evaluation_count == 0
    assert stats.mae is None
    assert stats.average_accuracy_score is None


def test_rejects_identity_or_horizon_mismatch_for_certified_evidence() -> None:
    bad = _evaluation("eval-1")
    bad = ForecastEvaluationRecord(
        evaluation_id=bad.evaluation_id,
        result=ForecastEvaluationResult(
            **{**bad.result.to_dict(), "model_version": "2.0"}
        ),
    )

    with pytest.raises(ValueError, match="registered model version"):
        ModelPerformanceStatisticsService().summarize(
            _registry(),
            (_evidence("eval-1"),),
            (bad,),
        )

    with pytest.raises(ValueError, match="not supported"):
        ModelPerformanceStatisticsService().summarize(
            _registry(), (), (), forecast_horizon_days=30
        )


def test_f2_remains_read_only_and_does_not_rank_or_select_models() -> None:
    service = ModelPerformanceStatisticsService()
    stats = service.summarize(_registry(), (), ())
    payload = stats.to_dict()

    assert stats.advisory_only is True
    assert stats.read_only is True
    assert stats.inventory_source_of_truth_preserved is True
    assert {"rank", "ranking_score", "weight", "selected"}.isdisjoint(payload)
    assert not hasattr(service, "select")
    assert not hasattr(service, "rank")
