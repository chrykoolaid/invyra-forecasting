from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from invyra_forecasting.constants import Environment
from invyra_forecasting.orchestration import AdvisoryForecastRequest
from invyra_forecasting.signals import (
    ForecastSignal,
    ForecastSignalDirection,
    ForecastSignalSource,
    ForecastSignalType,
)


class ForecastSignalPayload(BaseModel):
    signal_id: str | None = None
    signal_type: ForecastSignalType
    module_source: ForecastSignalSource
    item_id: str
    sku: str
    location_id: str
    timestamp_utc: str | None = None
    quantity: float = Field(ge=0)
    unit: str = "unit"
    direction: ForecastSignalDirection
    reason_code: str | None = None
    confidence: float = Field(default=1.0, ge=0, le=1)
    evidence_ref: str | None = None
    event_version: str = "1.0"
    environment: Environment = Environment.TRAINING
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_signal(self) -> ForecastSignal:
        return ForecastSignal.create(
            signal_type=self.signal_type,
            module_source=self.module_source,
            item_id=self.item_id,
            sku=self.sku,
            location_id=self.location_id,
            quantity=self.quantity,
            unit=self.unit,
            direction=self.direction,
            reason_code=self.reason_code,
            confidence=self.confidence,
            evidence_ref=self.evidence_ref,
            event_version=self.event_version,
            environment=self.environment,
            metadata=self.metadata,
            timestamp_utc=self.timestamp_utc,
            signal_id=self.signal_id,
        )


class AdvisoryForecastApiRequest(BaseModel):
    item_id: str
    location_id: str
    environment: Environment = Environment.TRAINING
    analysis_window_days: int = Field(default=30, ge=1, le=730)
    forecast_days: int = Field(default=30, ge=1, le=365)
    signals: list[ForecastSignalPayload] = Field(default_factory=list)

    def to_orchestration_request(self) -> AdvisoryForecastRequest:
        return AdvisoryForecastRequest(
            item_id=self.item_id,
            location_id=self.location_id,
            environment=self.environment,
            analysis_window_days=self.analysis_window_days,
            forecast_days=self.forecast_days,
        )
