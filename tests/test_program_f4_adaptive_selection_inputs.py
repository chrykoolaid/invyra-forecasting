from dataclasses import FrozenInstanceError

import pytest

from invyra_forecasting.adaptive_selection_inputs import (
    AdaptiveSelectionContext,
    AdaptiveSelectionInputBuilder,
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


def _registry(*, model_version: str = "1.0") -> ModelPerformanceRegistryEntry:
    return ModelPerformanceRegistryEntry(
        registry_id=f"registry-{model_version}",
        model_name="seasonal-naive",
        model_version=model_version,
        lifecycle_status=ModelLifecycleStatus.ACTIVE,
        supported_forecast_horizons=(7, 14, 28),
        supported_demand_profiles=("seasonal", "stable"),
        namespace="default",
        registered_at_utc="2026-07-15T16:00:00+00:00",
    )


def _statistics(*, model_version: str = "1.0", horizon: int = 7) -> ModelPerformanceStatistics:
    return ModelPerformanceStatistics(
        registry_id=f"registry-{model_version}",
        model_name="seasonal-naive",
        model_version=model_version,
        forecast_horizon_days=horizon,
        eligible_evaluation_count=30,
        mae=2.0,
        rmse=2.5,
        mape=0.2,
        bias=0.1,
        average_accuracy_score=0.8,
        average_calibration_gap=0.05,
    )


def _confidence(*, model_version: str = "1.0", horizon: int = 7) -> ModelConfidenceAssessment:
    return ModelConfidenceAssessment(
        registry_id=f"registry-{model_version}",
        model_name="seasonal-naive",
        model_version=model_version,
        forecast_horizon_days=horizon,
        confidence_status=ModelConfidenceStatus.TRUSTED,
        eligible_evaluation_count=30,
        qualification_reasons=("30 to 99 certified evaluations",),
    )


def test_builds_immutable_governed_candidate_input() -> None:
    builder = AdaptiveSelectionInputBuilder()
    context = AdaptiveSelectionContext(
        forecast_horizon_days=7,
        demand_profile="seasonal",
        item_id="item-1",
        location_id="store-1",
    )

    candidate = builder.build_candidate(
        _registry(),
        _statistics(),
        _confidence(),
        context,
        evidence_refs=("eval-1", "eval-2", "eval-1"),
    )

    assert candidate.horizon_supported is True
    assert candidate.demand_profile_supported is True
    assert candidate.confidence_status == "trusted"
    assert candidate.average_accuracy_score == 0.8
    assert candidate.evidence_refs == ("eval-1", "eval-2")
    with pytest.raises(FrozenInstanceError):
        candidate.model_version = "2.0"


def test_reports_unsupported_context_without_selecting_or_rejecting_candidate() -> None:
    builder = AdaptiveSelectionInputBuilder()
    context = AdaptiveSelectionContext(
        forecast_horizon_days=90,
        demand_profile="intermittent",
    )
    statistics = ModelPerformanceStatistics(
        **{**_statistics().to_dict(), "forecast_horizon_days": None}
    )
    confidence = ModelConfidenceAssessment(
        **{**_confidence().to_dict(), "confidence_status": ModelConfidenceStatus.TRUSTED, "forecast_horizon_days": None}
    )

    candidate = builder.build_candidate(
        _registry(), statistics, confidence, context
    )

    assert candidate.horizon_supported is False
    assert candidate.demand_profile_supported is False
    assert any("not supported" in reason for reason in candidate.qualification_reasons)


def test_rejects_cross_contract_identity_and_count_mismatch() -> None:
    builder = AdaptiveSelectionInputBuilder()
    context = AdaptiveSelectionContext(forecast_horizon_days=7)

    with pytest.raises(ValueError, match="statistics must match"):
        builder.build_candidate(
            _registry(),
            _statistics(model_version="2.0"),
            _confidence(),
            context,
        )

    mismatched_confidence = ModelConfidenceAssessment(
        **{**_confidence().to_dict(), "confidence_status": ModelConfidenceStatus.TRUSTED, "eligible_evaluation_count": 31}
    )
    with pytest.raises(ValueError, match="evidence count"):
        builder.build_candidate(
            _registry(), _statistics(), mismatched_confidence, context
        )


def test_rejects_horizon_mismatch_between_context_and_statistics() -> None:
    with pytest.raises(ValueError, match="statistics horizon"):
        AdaptiveSelectionInputBuilder().build_candidate(
            _registry(),
            _statistics(horizon=14),
            _confidence(horizon=14),
            AdaptiveSelectionContext(forecast_horizon_days=7),
        )


def test_builds_unique_package_with_shared_context() -> None:
    builder = AdaptiveSelectionInputBuilder()
    context = AdaptiveSelectionContext(forecast_horizon_days=7)
    first = builder.build_candidate(
        _registry(model_version="1.0"),
        _statistics(model_version="1.0"),
        _confidence(model_version="1.0"),
        context,
    )
    second = builder.build_candidate(
        _registry(model_version="2.0"),
        _statistics(model_version="2.0"),
        _confidence(model_version="2.0"),
        context,
    )

    package = builder.build_package(context, (first, second))

    assert len(package.candidates) == 2
    assert package.context.forecast_horizon_days == 7
    assert package.advisory_only is True
    assert package.read_only is True

    with pytest.raises(ValueError, match="unique"):
        builder.build_package(context, (first, first))


def test_f4_does_not_score_rank_select_or_mutate_models() -> None:
    builder = AdaptiveSelectionInputBuilder()
    candidate = builder.build_candidate(
        _registry(),
        _statistics(),
        _confidence(),
        AdaptiveSelectionContext(forecast_horizon_days=7),
    )
    payload = candidate.to_dict()

    forbidden = {"score", "ranking_score", "rank", "weight", "selected_model_id"}
    assert forbidden.isdisjoint(payload)
    assert not hasattr(builder, "score_model")
    assert not hasattr(builder, "rank_models")
    assert not hasattr(builder, "select")
    assert not hasattr(builder, "update_lifecycle")
