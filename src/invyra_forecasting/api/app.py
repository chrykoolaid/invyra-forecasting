from __future__ import annotations

try:
    from fastapi import FastAPI
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("FastAPI is optional. Install API dependencies with: pip install -e '.[api]'") from exc

from invyra_forecasting import __version__

app = FastAPI(title="Invyra Forecasting Engine", version=__version__, description="Optional internal API wrapper for the Python-first forecasting engine.")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "engine": "invyra-forecasting", "version": __version__, "mode": "advisory"}


@app.post("/forecasts/item")
def forecast_item(payload: dict) -> dict:
    return {"status": "not_implemented_for_raw_payload_yet", "message": "Phase 1 API shell is present. Use the Python service for full typed forecasts.", "received_keys": sorted(payload.keys())}


@app.post("/forecasts/batch")
def forecast_batch(payload: dict) -> dict:
    return {"status": "not_implemented_for_raw_payload_yet", "message": "Batch endpoint shell is reserved for module integration.", "received_keys": sorted(payload.keys())}


@app.post("/risk/stockout")
def stockout_risk(payload: dict) -> dict:
    return {"status": "not_implemented_for_raw_payload_yet", "message": "Risk endpoint shell is reserved for module integration.", "received_keys": sorted(payload.keys())}


@app.post("/recommendations/reorder")
def reorder_recommendation(payload: dict) -> dict:
    return {"status": "not_implemented_for_raw_payload_yet", "message": "Recommendation endpoint shell is reserved for module integration.", "received_keys": sorted(payload.keys())}
