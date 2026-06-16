from __future__ import annotations

try:
    from fastapi import FastAPI, HTTPException
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("FastAPI is optional. Install API dependencies with: pip install -e '.[api]'") from exc

from invyra_forecasting import __version__
from invyra_forecasting.api.contracts import BatchForecastRequest, ForecastRequest, OverrideAuditRequest
from invyra_forecasting.api.serializers import to_primitive
from invyra_forecasting.audit import create_override_audit_event
from invyra_forecasting.config import ForecastingConfig
from invyra_forecasting.data.validation import ValidationError
from invyra_forecasting.services import ForecastingService

app = FastAPI(title="Invyra Forecasting Engine", version=__version__, description="Optional internal API wrapper for the Python-first forecasting engine.")


def _config_from_request(request: ForecastRequest) -> ForecastingConfig:
    return ForecastingConfig(
        environment=request.environment,
        forecast_horizon_days=request.forecast_horizon_days,
        demand_lookback_days=request.demand_lookback_days,
        target_cover_days=request.target_cover_days,
        safety_stock_days=request.safety_stock_days,
    )


def _run_snapshot(request: ForecastRequest):
    try:
        service = ForecastingService(_config_from_request(request))
        return service.run_item_forecast(request.to_bundle(), actor=request.actor, anchor_date=request.anchor_date, write_snapshot=request.write_snapshot)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "engine": "invyra-forecasting", "version": __version__, "mode": "advisory"}


@app.post("/forecasts/item")
def forecast_item(payload: ForecastRequest) -> dict:
    return to_primitive(_run_snapshot(payload))


@app.post("/forecasts/batch")
def forecast_batch(payload: BatchForecastRequest) -> dict:
    snapshots = []
    for request in payload.requests:
        request.actor = payload.actor
        request.write_snapshot = payload.write_snapshots
        snapshots.append(_run_snapshot(request))
    return {"count": len(snapshots), "snapshots": to_primitive(snapshots)}


@app.post("/risk/stockout")
def stockout_risk(payload: ForecastRequest) -> dict:
    snapshot = _run_snapshot(payload)
    return {"risk": to_primitive(snapshot.risk), "confidence": to_primitive(snapshot.confidence), "explanation": to_primitive(snapshot.explanation)}


@app.post("/recommendations/reorder")
def reorder_recommendation(payload: ForecastRequest) -> dict:
    snapshot = _run_snapshot(payload)
    return {"recommendation": to_primitive(snapshot.recommendation), "risk": to_primitive(snapshot.risk), "confidence": to_primitive(snapshot.confidence), "explanation": to_primitive(snapshot.explanation)}


@app.post("/audit/override")
def audit_override(payload: OverrideAuditRequest) -> dict:
    event = create_override_audit_event(payload.actor, payload.environment, payload.item_id, payload.location_id, payload.original_recommendation, payload.override_action, payload.reason)
    return {"audit_event": to_primitive(event)}
