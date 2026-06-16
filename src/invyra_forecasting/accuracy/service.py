from __future__ import annotations

from invyra_forecasting.accuracy.entities import ActualDemandRecord, ForecastAccuracyResult
from invyra_forecasting.accuracy.metrics import calculate_accuracy_metrics, validate_actuals_match
from invyra_forecasting.accuracy.store import JsonlAccuracyStore
from invyra_forecasting.config import ForecastingConfig
from invyra_forecasting.constants import Environment


class AccuracyService:
    """Evaluates forecast quality against actual demand."""

    def __init__(self, config: ForecastingConfig | None = None) -> None:
        self.config = config or ForecastingConfig.from_env()
        self.store = JsonlAccuracyStore(self.config.accuracy_log_path)

    def evaluate(
        self,
        item_id: str,
        location_id: str,
        environment: Environment,
        forecast_quantity: float,
        actuals: list[ActualDemandRecord],
        forecast_horizon_days: int,
        forecast_snapshot_id: str | None = None,
        persist: bool = False,
        details: dict | None = None,
    ) -> ForecastAccuracyResult:
        validate_actuals_match(actuals, item_id, location_id, environment)
        actual_quantity = sum(actual.quantity for actual in actuals)
        result = calculate_accuracy_metrics(
            forecast_quantity=forecast_quantity,
            actual_quantity=actual_quantity,
            item_id=item_id,
            location_id=location_id,
            environment=environment,
            forecast_horizon_days=forecast_horizon_days,
            actual_record_count=len(actuals),
            forecast_snapshot_id=forecast_snapshot_id,
            details=details,
        )
        if persist:
            self.store.append(result)
        return result

    def list_item_accuracy(self, item_id: str, location_id: str | None = None, environment: Environment | str | None = None, limit: int | None = 100) -> list[dict]:
        return self.store.list_results(limit=limit, item_id=item_id, location_id=location_id, environment=environment)
