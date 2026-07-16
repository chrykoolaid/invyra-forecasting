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
from invyra_forecasting.operational_portfolio_summary import (
    OperationalForecastPortfolioSummaryService,
)

router = APIRouter(tags=["operational-portfolio-intelligence"])


@router.get("/v1/intelligence/operational/portfolio/summary")
def get_operational_forecast_portfolio_summary(as_of_utc: str | None = None) -> dict:
    resolved_as_of = as_of_utc or datetime.now(timezone.utc).isoformat()
    repository = FileForecastHistoryRepository(
        os.getenv("INVYRA_FORECAST_HISTORY_DIR", "data/history")
    )
    try:
        summary = OperationalForecastPortfolioSummaryService().summarize(
            repository.all(),
            as_of_utc=resolved_as_of,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return production_envelope(
        "operational_forecast_portfolio_summary",
        summary.to_dict(),
    )
