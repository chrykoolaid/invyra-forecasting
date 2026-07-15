from contextlib import contextmanager
from dataclasses import FrozenInstanceError

import pytest

from invyra_forecasting.api import tenant_context
from invyra_forecasting.enterprise_intelligence_summary import (
    EnterpriseForecastIntelligenceSummaryService,
    EnterpriseModelIntelligenceInput,
)
from invyra_forecasting.model_confidence_governance import (
    ModelConfidenceAssessment,
    ModelConfidenceStatus,
)
from invyra_forecasting.model_performance_registry import (
    ModelLifecycleStatus,
    ModelPerformanceRegistryEntry,
)
from invyra_forecasting.model_performance_statistics import ModelPerformanceStatistics


@contextmanager
def _tenant(tenant_id: str):
    token = tenant_context._TENANT_ID.set(tenant_context.normalize_tenant_id(tenant_id))
    try:
        yield
    finally:
        tenant_context._TENANT_ID.reset(token)


def _input(
    registry_id: str,
    model_name: str,
    *,
    count: int,
    accuracy: float | None,
    calibration: float | None,
    confidence: ModelConfidenceStatus,
    namespace: str = "tenant-a",
) -> EnterpriseModelIntelligenceInput:
    registry = ModelPerformanceRegistryEntry(
        registry_id=registry_id,
        model_name=model_name,
        model_version="1.0",
        lifecycle_status=ModelLifecycleStatus.ACTIVE,
        supported_forecast_horizons=(7,),
        supported_demand_profiles=("seasonal",),
        namespace=namespace,
        registered_at_utc="2026-07-16T00:00:00+00:00",
    )
    statistics = ModelPerformanceStatistics(
        registry_id=registry_id,
        model_name=model_name,
        model_version="1.0",
        forecast_horizon_days=7,
        eligible_evaluation_count=count,
        mae=None if count == 0 else 2.0,
        rmse=None if count == 0 else 2.5,
        mape=None if count == 0 else 0.2,
        bias=None if count == 0 else 0.05,
        average_accuracy_score=accuracy,
        average_calibration_gap=calibration,
    )
    assessment = ModelConfidenceAssessment(
        registry_id=registry_id,
        model_name=model_name,
        model_version="1.0",
        forecast_horizon_days=7,
        confidence_status=confidence,
        eligible_evaluation_count=count,
        qualification_reasons=("certified evidence depth",),
    )
    return EnterpriseModelIntelligenceInput(
        registry_entry=registry,
        statistics=statistics,
        confidence=assessment,
        evidence_refs=() if count == 0 else (f"evaluation-{registry_id}",),
    )


def test_summarizes_certified_portfolio_intelligence_deterministically() -> None:
    with _tenant("tenant-a"):
        summary = EnterpriseForecastIntelligenceSummaryService().summarize(
            (
                _input("reg-b", "moving-average", count=30, accuracy=0.8, calibration=0.1, confidence=ModelConfidenceStatus.TRUSTED),
                _input("reg-a", "seasonal-naive", count=10, accuracy=0.9, calibration=0.05, confidence=ModelConfidenceStatus.DEVELOPING),
                _input("reg-c", "croston", count=0, accuracy=None, calibration=None, confidence=ModelConfidenceStatus.EXPERIMENTAL),
            ),
            as_of_utc="2026-07-16T08:00:00+08:00",
        )

    assert summary.as_of_utc == "2026-07-16T08:00:00+08:00"
    assert summary.model_version_count == 3
    assert summary.evaluated_model_version_count == 2
    assert summary.total_eligible_evaluation_count == 40
    assert summary.weighted_average_accuracy_score == 0.825
    assert summary.weighted_average_calibration_gap == 0.0875
    assert summary.confidence_distribution["trusted"] == 1
    assert summary.confidence_distribution["developing"] == 1
    assert summary.confidence_distribution["experimental"] == 1
    assert [model.model_name for model in summary.models] == ["croston", "moving-average", "seasonal-naive"]


def test_empty_portfolio_is_valid_and_does_not_invent_metrics() -> None:
    with _tenant("tenant-a"):
        summary = EnterpriseForecastIntelligenceSummaryService().summarize(
            (), as_of_utc="2026-07-16T00:00:00+00:00"
        )

    assert summary.model_version_count == 0
    assert summary.total_eligible_evaluation_count == 0
    assert summary.weighted_average_accuracy_score is None
    assert summary.models == ()


def test_rejects_cross_tenant_or_mismatched_evidence() -> None:
    with _tenant("tenant-a"):
        with pytest.raises(ValueError, match="active tenant namespace"):
            EnterpriseForecastIntelligenceSummaryService().summarize(
                (_input("reg-x", "baseline", count=10, accuracy=0.8, calibration=0.1, confidence=ModelConfidenceStatus.DEVELOPING, namespace="tenant-b"),),
                as_of_utc="2026-07-16T00:00:00+00:00",
            )

    item = _input("reg-a", "baseline", count=10, accuracy=0.8, calibration=0.1, confidence=ModelConfidenceStatus.DEVELOPING)
    with pytest.raises(ValueError, match="evidence references"):
        EnterpriseModelIntelligenceInput(
            registry_entry=item.registry_entry,
            statistics=item.statistics,
            confidence=item.confidence,
            evidence_refs=(),
        )


def test_summary_is_immutable_serializable_and_advisory_only() -> None:
    with _tenant("tenant-a"):
        service = EnterpriseForecastIntelligenceSummaryService()
        summary = service.summarize(
            (_input("reg-a", "baseline", count=10, accuracy=0.8, calibration=0.1, confidence=ModelConfidenceStatus.DEVELOPING),),
            as_of_utc="2026-07-16T00:00:00+00:00",
        )

    with pytest.raises(FrozenInstanceError):
        summary.model_version_count = 2
    payload = summary.to_dict()
    assert payload["models"][0]["evidence_refs"] == ["evaluation-reg-a"]
    assert payload["advisory_only"] is True
    assert payload["read_only"] is True
    assert payload["inventory_source_of_truth_preserved"] is True
    assert not hasattr(service, "rank")
    assert not hasattr(service, "select")
    assert not hasattr(service, "recommend")
    assert not hasattr(service, "mutate_inventory")
