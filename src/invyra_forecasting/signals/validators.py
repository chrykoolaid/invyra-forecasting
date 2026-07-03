from __future__ import annotations

from invyra_forecasting.signals.schema import ForecastSignal


class ForecastSignalValidationError(ValueError):
    """Raised when a forecasting signal violates the registry contract."""


REQUIRED_TEXT_FIELDS = {
    "signal_id": "signal_id is required",
    "item_id": "item_id is required",
    "sku": "sku is required",
    "location_id": "location_id is required",
    "timestamp_utc": "timestamp_utc is required",
    "unit": "unit is required",
    "event_version": "event_version is required",
}


def validate_forecast_signal(signal: ForecastSignal) -> None:
    """Validate a normalized forecast signal before registry ingestion."""

    for field_name, message in REQUIRED_TEXT_FIELDS.items():
        value = getattr(signal, field_name)
        if not isinstance(value, str) or not value.strip():
            raise ForecastSignalValidationError(message)

    if signal.quantity < 0:
        raise ForecastSignalValidationError("quantity must be zero or greater")

    if signal.confidence < 0 or signal.confidence > 1:
        raise ForecastSignalValidationError("confidence must be between 0 and 1")

    if signal.evidence_ref is not None and not signal.evidence_ref.strip():
        raise ForecastSignalValidationError("evidence_ref must not be blank when supplied")

    if not signal.timestamp_utc.endswith("Z"):
        raise ForecastSignalValidationError("timestamp_utc must be UTC ISO-8601 text ending in Z")
