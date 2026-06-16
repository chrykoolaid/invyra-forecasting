from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime
from typing import Any
from uuid import uuid4

from invyra_forecasting.constants import Environment


@dataclass(frozen=True)
class ActualDemandRecord:
    item_id: str
    location_id: str
    actual_date: date
    quantity: float
    environment: Environment = Environment.TRAINING


@dataclass(frozen=True)
class ForecastAccuracyResult:
    accuracy_id: str
    forecast_snapshot_id: str | None
    item_id: str
    location_id: str
    environment: Environment
    forecast_horizon_days: int
    forecast_quantity: float
    actual_quantity: float
    error: float
    absolute_error: float
    percentage_error: float | None
    mean_absolute_error: float
    mean_absolute_percentage_error: float | None
    accuracy_score: float
    accuracy_rating: str
    bias: str
    actual_record_count: int
    evaluated_at_utc: str
    details: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        forecast_snapshot_id: str | None,
        item_id: str,
        location_id: str,
        environment: Environment,
        forecast_horizon_days: int,
        forecast_quantity: float,
        actual_quantity: float,
        error: float,
        absolute_error: float,
        percentage_error: float | None,
        accuracy_score: float,
        accuracy_rating: str,
        bias: str,
        actual_record_count: int,
        details: dict[str, Any] | None = None,
    ) -> "ForecastAccuracyResult":
        return cls(
            accuracy_id=str(uuid4()),
            forecast_snapshot_id=forecast_snapshot_id,
            item_id=item_id,
            location_id=location_id,
            environment=environment,
            forecast_horizon_days=forecast_horizon_days,
            forecast_quantity=round(forecast_quantity, 4),
            actual_quantity=round(actual_quantity, 4),
            error=round(error, 4),
            absolute_error=round(absolute_error, 4),
            percentage_error=None if percentage_error is None else round(percentage_error, 4),
            mean_absolute_error=round(absolute_error, 4),
            mean_absolute_percentage_error=None if percentage_error is None else round(percentage_error, 4),
            accuracy_score=round(accuracy_score, 4),
            accuracy_rating=accuracy_rating,
            bias=bias,
            actual_record_count=actual_record_count,
            evaluated_at_utc=datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
            details=details or {},
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
