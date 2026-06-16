from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date
from pathlib import Path

from invyra_forecasting.audit import create_forecast_audit_event
from invyra_forecasting.config import ForecastingConfig
from invyra_forecasting.confidence import score_confidence
from invyra_forecasting.data.validation import validate_forecast_input
from invyra_forecasting.explanation import build_explanation
from invyra_forecasting.models import SimpleDemandForecaster
from invyra_forecasting.recommendations import build_reorder_recommendation
from invyra_forecasting.risk import score_inventory_risk
from invyra_forecasting.schemas import ForecastInputBundle, ForecastSnapshot


class ForecastingService:
    """Orchestrates explainable Phase 1 forecasting."""

    def __init__(self, config: ForecastingConfig | None = None) -> None:
        self.config = config or ForecastingConfig()

    def run_item_forecast(self, bundle: ForecastInputBundle, actor: str = "system", anchor_date: date | None = None, write_snapshot: bool = False) -> ForecastSnapshot:
        validate_forecast_input(bundle)
        forecaster = SimpleDemandForecaster(self.config.demand_lookback_days, self.config.forecast_horizon_days)
        forecast = forecaster.forecast(bundle, anchor_date=anchor_date)
        risk = score_inventory_risk(bundle, forecast, self.config.target_cover_days, anchor_date=anchor_date)
        recommendation = build_reorder_recommendation(bundle, forecast, risk, self.config.safety_stock_days, self.config.target_cover_days)
        confidence = score_confidence(bundle, self.config.demand_lookback_days, anchor_date=anchor_date)
        explanation = build_explanation(bundle, forecast, risk, recommendation, confidence)
        audit_event = create_forecast_audit_event(actor, bundle.environment, bundle.item.item_id, bundle.location.location_id, {"method": forecast.method, "advisory_only": True})
        snapshot = ForecastSnapshot.create(
            input_summary={"item_id": bundle.item.item_id, "location_id": bundle.location.location_id, "stock_available": bundle.stock_position.available, "movement_count": len(bundle.movements), "supplier_lead_time_days": bundle.supplier_profile.lead_time_days, "environment": bundle.environment.value},
            forecast=forecast,
            risk=risk,
            recommendation=recommendation,
            confidence=confidence,
            explanation=explanation,
            audit_event=audit_event,
        )
        if write_snapshot:
            self.write_snapshot(snapshot)
        return snapshot

    def run_batch_forecast(self, bundles: list[ForecastInputBundle], actor: str = "system", anchor_date: date | None = None, write_snapshots: bool = False) -> list[ForecastSnapshot]:
        return [self.run_item_forecast(bundle, actor=actor, anchor_date=anchor_date, write_snapshot=write_snapshots) for bundle in bundles]

    def write_snapshot(self, snapshot: ForecastSnapshot) -> Path:
        snapshot_dir = Path(self.config.snapshot_dir)
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        path = snapshot_dir / f"{snapshot.snapshot_id}.json"
        path.write_text(json.dumps(asdict(snapshot), indent=2, default=str), encoding="utf-8")
        return path
