from __future__ import annotations

from invyra_forecasting.constants import Environment
from invyra_forecasting.accuracy.entities import ActualDemandRecord, ForecastAccuracyResult


class AccuracyValidationError(ValueError):
    """Raised when accuracy evaluation inputs are invalid."""


def _bias(forecast_quantity: float, actual_quantity: float, percentage_error: float | None) -> str:
    if actual_quantity == 0 and forecast_quantity == 0:
        return "No Actual Demand"
    if percentage_error is not None and percentage_error <= 5:
        return "On Target"
    if forecast_quantity > actual_quantity:
        return "Over Forecast"
    if forecast_quantity < actual_quantity:
        return "Under Forecast"
    return "On Target"


def _rating(score: float) -> str:
    if score >= 85:
        return "High"
    if score >= 65:
        return "Medium"
    return "Low"


def calculate_accuracy_metrics(
    forecast_quantity: float,
    actual_quantity: float,
    item_id: str,
    location_id: str,
    environment: Environment,
    forecast_horizon_days: int,
    actual_record_count: int,
    forecast_snapshot_id: str | None = None,
    details: dict | None = None,
) -> ForecastAccuracyResult:
    if forecast_quantity < 0:
        raise AccuracyValidationError("forecast_quantity cannot be negative")
    if actual_quantity < 0:
        raise AccuracyValidationError("actual_quantity cannot be negative")
    if forecast_horizon_days <= 0:
        raise AccuracyValidationError("forecast_horizon_days must be positive")
    error = forecast_quantity - actual_quantity
    absolute_error = abs(error)
    percentage_error = None if actual_quantity == 0 else (absolute_error / actual_quantity) * 100
    if actual_quantity == 0:
        accuracy_score = 100.0 if forecast_quantity == 0 else 0.0
    else:
        accuracy_score = max(0.0, 100.0 - min(100.0, percentage_error or 0.0))
    return ForecastAccuracyResult.create(
        forecast_snapshot_id=forecast_snapshot_id,
        item_id=item_id,
        location_id=location_id,
        environment=environment,
        forecast_horizon_days=forecast_horizon_days,
        forecast_quantity=forecast_quantity,
        actual_quantity=actual_quantity,
        error=error,
        absolute_error=absolute_error,
        percentage_error=percentage_error,
        accuracy_score=accuracy_score,
        accuracy_rating=_rating(accuracy_score),
        bias=_bias(forecast_quantity, actual_quantity, percentage_error),
        actual_record_count=actual_record_count,
        details=details,
    )


def validate_actuals_match(actuals: list[ActualDemandRecord], item_id: str, location_id: str, environment: Environment) -> None:
    for actual in actuals:
        if actual.item_id != item_id:
            raise AccuracyValidationError(f"actual item_id mismatch: expected {item_id}, got {actual.item_id}")
        if actual.location_id != location_id:
            raise AccuracyValidationError(f"actual location_id mismatch: expected {location_id}, got {actual.location_id}")
        if actual.environment != environment:
            raise AccuracyValidationError(f"actual environment mismatch: expected {environment.value}, got {actual.environment.value}")
        if actual.quantity < 0:
            raise AccuracyValidationError("actual quantity cannot be negative")
