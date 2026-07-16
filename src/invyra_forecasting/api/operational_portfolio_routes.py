from __future__ import annotations

import os
from datetime import datetime, timezone

try:
    from fastapi import APIRouter, HTTPException
except ImportError as exc:  # pragma: no cover
    raise RuntimeError(
        "FastAPI is optional. Install API dependencies with: pip install -e '.[api]'"
    ) from exc

from invyra_forecasting.api.production_contracts import production_envelope
from invyra_forecasting.history_persistence import FileForecastHistoryRepository
from invyra_forecasting.operational_portfolio_breakdown import (
    OperationalForecastPortfolioBreakdownService,
)
from invyra_forecasting.operational_portfolio_summary import (
    OperationalForecastPortfolioSummaryService,
)

router = APIRouter(tags=["operational-portfolio-intelligence"])


def _history_repository() -> FileForecastHistoryRepository:
    return FileForecastHistoryRepository(
        os.getenv("INVYRA_FORECAST_HISTORY_DIR", "data/history")
    )


def _resolved_as_of(as_of_utc: str | None) -> str:
    return as_of_utc or datetime.now(timezone.utc).isoformat()


@router.get("/v1/intelligence/operational/portfolio/summary")
def get_operational_forecast_portfolio_summary(as_of_utc: str | None = None) -> dict:
    resolved_as_of = _resolved_as_of(as_of_utc)
    try:
        summary = OperationalForecastPortfolioSummaryService().summarize(
            _history_repository().all(),
            as_of_utc=resolved_as_of,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return production_envelope(
        "operational_forecast_portfolio_summary",
        summary.to_dict(),
    )


@router.get("/v1/intelligence/operational/portfolio/breakdown")
def get_operational_forecast_portfolio_breakdown(as_of_utc: str | None = None) -> dict:
    resolved_as_of = _resolved_as_of(as_of_utc)
    try:
        breakdown = OperationalForecastPortfolioBreakdownService().breakdown(
            _history_repository().all(),
            as_of_utc=resolved_as_of,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return production_envelope(
        "operational_forecast_portfolio_breakdown",
        breakdown.to_dict(),
    )
