from dataclasses import fields, is_dataclass

from invyra_forecasting.api.enterprise_intelligence_routes import router
from invyra_forecasting.certified_statistics_persistence import (
    CertifiedModelPerformanceStatisticsRecord,
    InMemoryCertifiedStatisticsRepository,
)
from invyra_forecasting.enterprise_forecast_health import (
    EnterpriseForecastHealth,
    EnterpriseForecastHealthPolicy,
)
from invyra_forecasting.enterprise_intelligence_summary import (
    EnterpriseForecastIntelligenceSummary,
    EnterpriseForecastIntelligenceSummaryService,
)
from invyra_forecasting.enterprise_portfolio_comparison import (
    EnterprisePortfolioComparison,
    EnterprisePortfolioComparisonService,
)
from invyra_forecasting.enterprise_portfolio_risk import (
    EnterprisePortfolioRiskAssessment,
    EnterprisePortfolioRiskPolicy,
)
from invyra_forecasting.executive_intelligence_brief import (
    ExecutiveIntelligenceBrief,
    ExecutiveIntelligenceBriefService,
)


PROHIBITED_INTELLIGENCE_METHODS = {
    "recommend",
    "rank",
    "score",
    "select",
    "predict",
    "retrain",
    "tune",
    "retire",
    "disable",
    "mutate_inventory",
    "mutate_stock",
    "create_purchase_order",
    "approve_purchase_order",
}


def test_program_g_top_level_contracts_remain_immutable_and_governed() -> None:
    for contract in (
        EnterpriseForecastIntelligenceSummary,
        EnterpriseForecastHealth,
        EnterprisePortfolioRiskAssessment,
        EnterprisePortfolioComparison,
        ExecutiveIntelligenceBrief,
        CertifiedModelPerformanceStatisticsRecord,
    ):
        assert is_dataclass(contract)
        assert contract.__dataclass_params__.frozen is True
        names = {field.name for field in fields(contract)}
        assert {"advisory_only", "read_only", "inventory_source_of_truth_preserved"} <= names


def test_program_g_services_expose_no_ranking_recommendation_or_operational_actions() -> None:
    services = (
        EnterpriseForecastIntelligenceSummaryService,
        EnterpriseForecastHealthPolicy,
        EnterprisePortfolioRiskPolicy,
        EnterprisePortfolioComparisonService,
        ExecutiveIntelligenceBriefService,
    )
    for service in services:
        exposed = {name for name in dir(service) if not name.startswith("_")}
        assert not (exposed & PROHIBITED_INTELLIGENCE_METHODS)


def test_program_g_service_surfaces_remain_narrow_and_deterministic() -> None:
    assert {
        name for name in dir(EnterpriseForecastIntelligenceSummaryService) if not name.startswith("_")
    } == {"summarize"}
    assert {name for name in dir(EnterpriseForecastHealthPolicy) if not name.startswith("_")} == {
        "classify"
    }
    assert {name for name in dir(EnterprisePortfolioRiskPolicy) if not name.startswith("_")} == {
        "assess"
    }
    assert {
        name for name in dir(EnterprisePortfolioComparisonService) if not name.startswith("_")
    } == {"compare"}
    assert {name for name in dir(ExecutiveIntelligenceBriefService) if not name.startswith("_")} == {
        "compose"
    }


def test_certified_statistics_repository_remains_append_only() -> None:
    exposed = {
        name for name in dir(InMemoryCertifiedStatisticsRepository) if not name.startswith("_")
    }
    assert "append" in exposed
    assert "all" in exposed
    assert "latest_by_identity" in exposed
    assert "latest_by_identity_as_of" in exposed
    assert "update" not in exposed
    assert "delete" not in exposed
    assert "remove" not in exposed


def test_enterprise_intelligence_api_remains_get_only() -> None:
    enterprise_routes = {
        route.path: set(route.methods or ())
        for route in router.routes
        if route.path.startswith("/v1/intelligence/enterprise/")
    }
    assert enterprise_routes == {
        "/v1/intelligence/enterprise/summary": {"GET"},
        "/v1/intelligence/enterprise/health": {"GET"},
        "/v1/intelligence/enterprise/risks": {"GET"},
        "/v1/intelligence/enterprise/compare": {"GET"},
        "/v1/intelligence/enterprise/brief": {"GET"},
    }
