from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from invyra_forecasting.accuracy.entities import ActualDemandRecord
from invyra_forecasting.constants import Environment


class ActualDemandPayload(BaseModel):
    item_id: str
    location_id: str
    actual_date: date
    quantity: float = Field(ge=0)
    environment: Environment = Environment.TRAINING

    def to_entity(self) -> ActualDemandRecord:
        return ActualDemandRecord(
            item_id=self.item_id,
            location_id=self.location_id,
            actual_date=self.actual_date,
            quantity=self.quantity,
            environment=self.environment,
        )


class AccuracyEvaluationRequest(BaseModel):
    actor: str = "api_accuracy"
    forecast_snapshot_id: str | None = None
    item_id: str
    location_id: str
    environment: Environment = Environment.TRAINING
    forecast_horizon_days: int = Field(default=30, ge=1, le=365)
    forecast_quantity: float = Field(ge=0)
    actuals: list[ActualDemandPayload] = Field(default_factory=list)
    persist: bool = False
    notes: str | None = None

    def to_actuals(self) -> list[ActualDemandRecord]:
        return [actual.to_entity() for actual in self.actuals]
