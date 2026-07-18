from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from invyra_forecasting.api.enterprise_intelligence_routes import _summary
from invyra_forecasting.api.operational_portfolio_routes import _portfolio_inputs
from invyra_forecasting.api.production_contracts import production_envelope
from invyra_forecasting.decision_context import DecisionContextService
from invyra_forecasting.decision_explanation import DecisionExplanationService
from invyra_forecasting.decision_priority import DecisionPriorityPolicy
from invyra_forecasting.enterprise_forecast_health import EnterpriseForecastHealthPolicy
from invyra_forecasting.enterprise_portfolio_risk import EnterprisePortfolioRiskPolicy
from invyra_forecasting.operational_portfolio_coverage import OperationalPortfolioCoveragePolicy
from invyra_forecasting.operational_portfolio_evidence_signals import OperationalPortfolioEvidenceSignalPolicy

router = APIRouter(tags=["decision-intelligence"])


@router.get("/v1/intelligence/decisions/review")
def get_decision_review(as_of_utc: str | None = None) -> dict:
    boundary = as_of_utc or datetime.now(timezone.utc).isoformat()
    try:
        enterprise_summary = _summary(boundary)
        enterprise_health = EnterpriseForecastHealthPolicy().classify(enterprise_summary)
        enterprise_risks = EnterprisePortfolioRiskPolicy().assess(enterprise_health)
        operational_summary, operational_breakdown = _portfolio_inputs(boundary)
        operational_coverage = OperationalPortfolioCoveragePolicy().classify(operational_summary, operational_breakdown)
        operational_signals = OperationalPortfolioEvidenceSignalPolicy().assess(operational_coverage, operational_breakdown)
        context = DecisionContextService().compose(
            enterprise_summary,
            enterprise_health,
            enterprise_risks,
            operational_summary,
            operational_coverage,
            operational_signals,
        )
        priority = DecisionPriorityPolicy().assess(context)
        explanation = DecisionExplanationService().explain(context, priority)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return production_envelope(
        "decision_review",
        {"context": context.to_dict(), "priority": priority.to_dict(), "explanation": explanation.to_dict()},
    )
