from invyra_forecasting.enterprise_forecast_health import (
    EnterpriseForecastHealthPolicy,
    EnterpriseForecastHealthStatus,
)
from invyra_forecasting.enterprise_intelligence_summary import (
    EnterpriseForecastIntelligenceSummary,
    EnterpriseModelIntelligence,
)


def _summary(*, models, accuracy=None, calibration=None):
    evaluated = sum(model.eligible_evaluation_count > 0 for model in models)
    return EnterpriseForecastIntelligenceSummary(
        namespace="tenant-a",
        as_of_utc="2026-07-16T00:00:00+00:00",
        model_version_count=len(models),
        evaluated_model_version_count=evaluated,
        total_eligible_evaluation_count=sum(model.eligible_evaluation_count for model in models),
        confidence_distribution={
            "experimental": 0,
            "limited_evidence": 0,
            "developing": 0,
            "trusted": 0,
            "enterprise_certified": 0,
        },
        weighted_average_accuracy_score=accuracy,
        weighted_average_calibration_gap=calibration,
        models=tuple(models),
    )


def _model(name, count, refs=()):
    return EnterpriseModelIntelligence(
        registry_id=name,
        model_name=name,
        model_version="1.0",
        lifecycle_status="active",
        forecast_horizon_days=30,
        confidence_status="trusted" if count else "experimental",
        eligible_evaluation_count=count,
        average_accuracy_score=0.9 if count else None,
        average_calibration_gap=0.1 if count else None,
        bias=0.0 if count else None,
        evidence_refs=tuple(refs),
    )


def test_unavailable_without_certified_evidence():
    health = EnterpriseForecastHealthPolicy().classify(_summary(models=[_model("a", 0)]))
    assert health.health_status is EnterpriseForecastHealthStatus.UNAVAILABLE
    assert health.evaluated_coverage_ratio == 0.0


def test_limited_when_less_than_half_portfolio_is_evaluated():
    health = EnterpriseForecastHealthPolicy().classify(
        _summary(models=[_model("a", 10), _model("b", 0), _model("c", 0)])
    )
    assert health.health_status is EnterpriseForecastHealthStatus.LIMITED


def test_healthy_and_strong_thresholds_are_deterministic():
    healthy = EnterpriseForecastHealthPolicy().classify(
        _summary(
            models=[_model("a", 10), _model("b", 10), _model("c", 10), _model("d", 0)],
            accuracy=0.82,
            calibration=0.18,
        )
    )
    strong = EnterpriseForecastHealthPolicy().classify(
        _summary(
            models=[_model("a", 100, ("eval-2",)), _model("b", 100, ("eval-1",))],
            accuracy=0.92,
            calibration=0.08,
        )
    )
    assert healthy.health_status is EnterpriseForecastHealthStatus.HEALTHY
    assert strong.health_status is EnterpriseForecastHealthStatus.STRONG
    assert strong.evidence_refs == ("eval-1", "eval-2")


def test_health_contract_is_advisory_only_and_exposes_no_actions():
    health = EnterpriseForecastHealthPolicy().classify(_summary(models=[]))
    assert health.advisory_only is True
    assert health.read_only is True
    assert health.inventory_source_of_truth_preserved is True
    assert {name for name in dir(EnterpriseForecastHealthPolicy) if not name.startswith("_")} == {"classify"}
