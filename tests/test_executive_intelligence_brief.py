import pytest

from invyra_forecasting.enterprise_forecast_health import (
    EnterpriseForecastHealth,
    EnterpriseForecastHealthStatus,
)
from invyra_forecasting.enterprise_intelligence_summary import (
    EnterpriseForecastIntelligenceSummary,
)
from invyra_forecasting.enterprise_portfolio_risk import EnterprisePortfolioRiskAssessment
from invyra_forecasting.executive_intelligence_brief import ExecutiveIntelligenceBriefService


def _inputs(namespace: str = "tenant-a", as_of: str = "2026-07-16T00:00:00+00:00"):
    summary = EnterpriseForecastIntelligenceSummary(
        namespace=namespace,
        as_of_utc=as_of,
        model_version_count=0,
        evaluated_model_version_count=0,
        total_eligible_evaluation_count=0,
        confidence_distribution={},
        weighted_average_accuracy_score=None,
        weighted_average_calibration_gap=None,
        models=(),
    )
    health = EnterpriseForecastHealth(
        namespace=namespace,
        as_of_utc=as_of,
        health_status=EnterpriseForecastHealthStatus.UNAVAILABLE,
        evaluated_coverage_ratio=0.0,
        model_version_count=0,
        evaluated_model_version_count=0,
        total_eligible_evaluation_count=0,
        weighted_average_accuracy_score=None,
        weighted_average_calibration_gap=None,
        classification_reasons=("no evidence",),
        evidence_refs=(),
    )
    risks = EnterprisePortfolioRiskAssessment(
        namespace=namespace,
        as_of_utc=as_of,
        signal_count=0,
        signals=(),
    )
    return summary, health, risks


def test_composes_existing_views_without_recalculation_or_action() -> None:
    brief = ExecutiveIntelligenceBriefService().compose(*_inputs())
    assert brief.summary.model_version_count == 0
    assert brief.health.health_status is EnterpriseForecastHealthStatus.UNAVAILABLE
    assert brief.risks.signal_count == 0
    assert brief.comparison is None
    assert brief.advisory_only is True
    assert brief.read_only is True
    assert "recommend" in brief.brief_reasons[1]


def test_rejects_cross_tenant_or_mismatched_timestamps() -> None:
    summary, health, risks = _inputs()
    other_summary, other_health, other_risks = _inputs(namespace="tenant-b")
    with pytest.raises(ValueError, match="matching tenant namespaces"):
        ExecutiveIntelligenceBriefService().compose(summary, other_health, risks)

    _, later_health, _ = _inputs(as_of="2026-07-17T00:00:00+00:00")
    with pytest.raises(ValueError, match="timestamps must match"):
        ExecutiveIntelligenceBriefService().compose(summary, later_health, risks)
