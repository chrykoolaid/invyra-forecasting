from dataclasses import fields, is_dataclass

from invyra_forecasting.api.operational_portfolio_routes import router
from invyra_forecasting.history_persistence import FileForecastHistoryRepository
from invyra_forecasting.operational_portfolio_breakdown import (
    OperationalForecastPortfolioBreakdown,
    OperationalForecastPortfolioBreakdownService,
)
from invyra_forecasting.operational_portfolio_coverage import (
    OperationalPortfolioCoverageAssessment,
    OperationalPortfolioCoveragePolicy,
)
from invyra_forecasting.operational_portfolio_evidence_signals import (
    OperationalPortfolioEvidenceSignalAssessment,
    OperationalPortfolioEvidenceSignalPolicy,
)
from invyra_forecasting.operational_portfolio_summary import (
    OperationalForecastPortfolioSummary,
    OperationalForecastPortfolioSummaryService,
)


PROHIBITED_OPERATIONAL_INTELLIGENCE_METHODS = {
    "recommend",
    "rank",
    "score",
    "select",
    "predict",
    "detect_anomaly",
    "classify_stock_risk",
    "infer_inventory",
    "mutate_inventory",
    "mutate_stock",
    "create_stock_movement",
    "create_purchase_order",
    "approve_purchase_order",
    "update_history",
    "delete_history",
}


def test_program_h_top_level_contracts_remain_immutable_and_governed() -> None:
    for contract in (
        OperationalForecastPortfolioSummary,
        OperationalForecastPortfolioBreakdown,
        OperationalPortfolioCoverageAssessment,
        OperationalPortfolioEvidenceSignalAssessment,
    ):
        assert is_dataclass(contract)
        assert contract.__dataclass_params__.frozen is True
        names = {field.name for field in fields(contract)}
        assert {"advisory_only", "read_only", "inventory_source_of_truth_preserved"} <= names


def test_program_h_services_expose_no_ranking_recommendation_or_operational_actions() -> None:
    services = (
        OperationalForecastPortfolioSummaryService,
        OperationalForecastPortfolioBreakdownService,
        OperationalPortfolioCoveragePolicy,
        OperationalPortfolioEvidenceSignalPolicy,
    )
    for service in services:
        exposed = {name for name in dir(service) if not name.startswith("_")}
        assert not (exposed & PROHIBITED_OPERATIONAL_INTELLIGENCE_METHODS)


def test_program_h_service_surfaces_remain_narrow_and_deterministic() -> None:
    assert {
        name for name in dir(OperationalForecastPortfolioSummaryService) if not name.startswith("_")
    } == {"summarize"}
    assert {
        name for name in dir(OperationalForecastPortfolioBreakdownService) if not name.startswith("_")
    } == {"breakdown"}
    assert {
        name for name in dir(OperationalPortfolioCoveragePolicy) if not name.startswith("_")
    } == {"classify"}
    assert {
        name for name in dir(OperationalPortfolioEvidenceSignalPolicy) if not name.startswith("_")
    } == {"assess"}


def test_forecast_history_repository_remains_append_only() -> None:
    exposed = {name for name in dir(FileForecastHistoryRepository) if not name.startswith("_")}
    assert {
        "append",
        "get",
        "all",
        "versions_for_forecast",
        "latest_for_forecast",
        "lineage",
        "load_into",
    } <= exposed
    assert "update" not in exposed
    assert "delete" not in exposed
    assert "remove" not in exposed
    assert "replace" not in exposed


def test_operational_intelligence_api_remains_get_only() -> None:
    operational_routes = {
        route.path: set(route.methods or ())
        for route in router.routes
        if route.path.startswith("/v1/intelligence/operational/portfolio/")
    }
    assert operational_routes == {
        "/v1/intelligence/operational/portfolio/summary": {"GET"},
        "/v1/intelligence/operational/portfolio/breakdown": {"GET"},
        "/v1/intelligence/operational/portfolio/coverage": {"GET"},
    }
