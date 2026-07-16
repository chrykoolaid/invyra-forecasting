from invyra_forecasting.enterprise_forecast_health import (
    EnterpriseForecastHealth,
    EnterpriseForecastHealthStatus,
)
from invyra_forecasting.enterprise_portfolio_risk import (
    EnterprisePortfolioRiskPolicy,
    EnterprisePortfolioRiskSeverity,
    EnterprisePortfolioRiskType,
)


def _health(**overrides):
    values = {
        "namespace": "tenant-a",
        "as_of_utc": "2026-07-16T00:00:00+00:00",
        "health_status": EnterpriseForecastHealthStatus.DEVELOPING,
        "evaluated_coverage_ratio": 0.75,
        "model_version_count": 4,
        "evaluated_model_version_count": 3,
        "total_eligible_evaluation_count": 60,
        "weighted_average_accuracy_score": 0.85,
        "weighted_average_calibration_gap": 0.15,
        "classification_reasons": ("test health",),
        "evidence_refs": ("evaluation-1",),
    }
    values.update(overrides)
    return EnterpriseForecastHealth(**values)


def test_emits_no_signals_for_healthy_observed_conditions() -> None:
    assessment = EnterprisePortfolioRiskPolicy().assess(_health())
    assert assessment.signal_count == 0
    assert assessment.signals == ()
    assert assessment.advisory_only is True
    assert assessment.read_only is True


def test_emits_explainable_fixed_risk_signals() -> None:
    assessment = EnterprisePortfolioRiskPolicy().assess(_health(
        evaluated_coverage_ratio=0.25,
        evaluated_model_version_count=1,
        weighted_average_accuracy_score=0.7,
        weighted_average_calibration_gap=0.3,
    ))
    assert [signal.risk_type for signal in assessment.signals] == [
        EnterprisePortfolioRiskType.LOW_COVERAGE,
        EnterprisePortfolioRiskType.WEAK_ACCURACY,
        EnterprisePortfolioRiskType.CALIBRATION_CONCERN,
    ]
    assert all(signal.severity is EnterprisePortfolioRiskSeverity.ELEVATED for signal in assessment.signals)
    assert all(signal.evidence_refs == ("evaluation-1",) for signal in assessment.signals)


def test_no_evidence_is_informational_not_predictive() -> None:
    assessment = EnterprisePortfolioRiskPolicy().assess(_health(
        health_status=EnterpriseForecastHealthStatus.UNAVAILABLE,
        evaluated_coverage_ratio=0.0,
        evaluated_model_version_count=0,
        total_eligible_evaluation_count=0,
        weighted_average_accuracy_score=None,
        weighted_average_calibration_gap=None,
        evidence_refs=(),
    ))
    assert assessment.signals[0].risk_type is EnterprisePortfolioRiskType.NO_EVIDENCE
    assert assessment.signals[0].severity is EnterprisePortfolioRiskSeverity.INFORMATIONAL
    exposed = {name for name in dir(EnterprisePortfolioRiskPolicy) if not name.startswith("_")}
    assert exposed == {"assess"}
