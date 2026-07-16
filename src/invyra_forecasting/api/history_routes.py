from __future__ import annotations

import os

try:
    from fastapi import APIRouter, HTTPException
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("FastAPI is optional. Install API dependencies with: pip install -e '.[api]'") from exc

from invyra_forecasting.api.production_contracts import production_envelope
from invyra_forecasting.history_index import HistoryIndexQuery
from invyra_forecasting.history_provider import DurableHistoryReadProvider

router = APIRouter(prefix="/v1/history", tags=["history"])


def _query_service():
    provider = DurableHistoryReadProvider.from_directories(
        history_dir=os.getenv("INVYRA_FORECAST_HISTORY_DIR", "data/history"),
        explainability_dir=os.getenv(
            "INVYRA_FORECAST_EXPLAINABILITY_DIR",
            "data/explainability",
        ),
    )
    return provider.build_query_service()


@router.get("")
def list_history(
    history_id: str | None = None,
    snapshot_id: str | None = None,
    forecast_id: str | None = None,
    version_number: int | None = None,
    created_at_utc: str | None = None,
    created_from_utc: str | None = None,
    created_to_utc: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> dict:
    try:
        result = _query_service().list(
            HistoryIndexQuery(
                history_id=history_id,
                snapshot_id=snapshot_id,
                forecast_id=forecast_id,
                version_number=version_number,
                created_at_utc=created_at_utc,
                created_from_utc=created_from_utc,
                created_to_utc=created_to_utc,
            ),
            limit=limit,
            offset=offset,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return production_envelope("forecast_history", result.to_dict())


@router.get("/forecasts/{forecast_id}/versions")
def get_forecast_versions(forecast_id: str) -> dict:
    result = _query_service().versions(forecast_id)
    return production_envelope(
        "forecast_history_versions",
        result.to_dict(),
        forecast_id=forecast_id,
    )


@router.get("/{history_id}/lineage")
def get_history_lineage(history_id: str) -> dict:
    result = _query_service().lineage(history_id)
    if result.total == 0:
        raise HTTPException(status_code=404, detail=f"History record not found: {history_id}")
    return production_envelope(
        "forecast_history_lineage",
        result.to_dict(),
        history_id=history_id,
    )


@router.get("/{history_id}")
def get_history_record(history_id: str) -> dict:
    item = _query_service().get(history_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"History record not found: {history_id}")
    return production_envelope(
        "forecast_history_record",
        item,
        history_id=history_id,
    )


# Attach independent absolute-path read-only routes before the unchanged app
# includes this router. Route objects retain their own full paths and tags.
from invyra_forecasting.api.evaluation_routes import router as evaluation_router  # noqa: E402
from invyra_forecasting.api.enterprise_intelligence_routes import (  # noqa: E402
    router as enterprise_intelligence_router,
)
from invyra_forecasting.api.operational_portfolio_routes import (  # noqa: E402
    router as operational_portfolio_router,
)

router.routes.extend(evaluation_router.routes)
router.routes.extend(enterprise_intelligence_router.routes)
router.routes.extend(operational_portfolio_router.routes)
