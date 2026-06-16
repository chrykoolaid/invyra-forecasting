from __future__ import annotations

from datetime import date
from pathlib import Path

from invyra_forecasting.audit import JsonlAuditStore, create_forecast_audit_event
from invyra_forecasting.config import ForecastingConfig
from invyra_forecasting.confidence import score_confidence
from invyra_forecasting.data.repositories import FileSnapshotRepository
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
        self.snapshot_repository = FileSnapshotRepository(self.config.snapshot_dir)
        self.audit_store = JsonlAuditStore(self.config.audit_log_path)

    def run_item_forecast(
        self,
        bundle: ForecastInputBundle,
        actor: str = "system",
        anchor_date: date | None = None,
        write_snapshot: bool = False,
        write_audit: bool | None = None,
    ) -> ForecastSnapshot:
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
        should_write_audit = write_snapshot if write_audit is None else write_audit
        if should_write_audit:
            self.audit_store.append(audit_event)
        return snapshot

    def run_batch_forecast(self, bundles: list[ForecastInputBundle], actor: str = "system", anchor_date: date | None = None, write_snapshots: bool = False) -> list[ForecastSnapshot]:
        return [self.run_item_forecast(bundle, actor=actor, anchor_date=anchor_date, write_snapshot=write_snapshots) for bundle in bundles]

    def write_snapshot(self, snapshot: ForecastSnapshot) -> Path:
        return self.snapshot_repository.save(snapshot)

    def get_snapshot(self, snapshot_id: str) -> dict | None:
        return self.snapshot_repository.get(snapshot_id)
