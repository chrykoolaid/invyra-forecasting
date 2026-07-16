import pytest

from invyra_forecasting.enterprise_forecast_health import (
    EnterpriseForecastHealthPolicy,
    EnterpriseForecastHealthStatus,
)
from invyra_forecasting.enterprise_intelligence_summary import EnterpriseForecastIntelligenceSummary
from invyra_forecasting.enterprise_portfolio_risk import EnterprisePortfolioRiskPolicy
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
    health = EnterpriseForecastHealthPolicy().classify(summary)
    risks = EnterprisePortfolioRiskPolicy().assess(health)
    return summary, health, risks


def test_composes_existing_views_without_recalculation_or_action() -> None:
    brief = ExecutiveIntelligenceBriefService().compose(*_inputs())
    assert brief.summary.model_version_count == 0
    assert brief.health.health_status == EnterpriseForecastHealthStatus.UNAVAILABLE
    assert brief.risks.signal_count == 1
    assert brief.comparison is None
    assert brief.advisory_only is True
    assert brief.read_only is True
    assert brief.inventory_source_of_truth_preserved is True


def test_rejects_cross_tenant_or_mismatched_timestamps() -> None:
    summary, _, risks = _inputs()
    _, other_health, _ = _inputs(namespace="tenant-b")
    with pytest.raises(ValueError, match="matching tenant namespaces"):
        ExecutiveIntelligenceBriefService().compose(summary, other_health, risks)

    _, later_health, _ = _inputs(as_of="2026-07-17T00:00:00+00:00")
    with pytest.raises(ValueError, match="timestamps must match"):
        ExecutiveIntelligenceBriefService().compose(summary, later_health, risks)
