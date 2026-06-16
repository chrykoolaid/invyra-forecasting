from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime
from typing import Any
from uuid import uuid4

from invyra_forecasting.constants import Environment, MovementType


@dataclass(frozen=True)
class Item:
    item_id: str
    sku: str
    name: str
    category: str
    unit_of_measure: str = "unit"
    minimum_order_quantity: int = 1


@dataclass(frozen=True)
class Location:
    location_id: str
    name: str
    location_type: str = "STORE"


@dataclass(frozen=True)
class StockPosition:
    item_id: str
    location_id: str
    on_hand: float
    reserved: float = 0
    environment: Environment = Environment.TRAINING

    @property
    def available(self) -> float:
        return max(0.0, self.on_hand - self.reserved)


@dataclass(frozen=True)
class StockMovement:
    movement_id: str
    item_id: str
    location_id: str
    movement_date: date
    movement_type: MovementType
    quantity: float
    environment: Environment = Environment.TRAINING


@dataclass(frozen=True)
class SupplierProfile:
    supplier_id: str
    item_id: str
    lead_time_days: int
    lead_time_variability_days: int = 0
    minimum_order_quantity: int = 1


@dataclass(frozen=True)
class ForecastInputBundle:
    item: Item
    location: Location
    stock_position: StockPosition
    movements: list[StockMovement]
    supplier_profile: SupplierProfile
    environment: Environment = Environment.TRAINING


@dataclass(frozen=True)
class ForecastResult:
    item_id: str
    location_id: str
    forecast_horizon_days: int
    forecast_quantity: float
    average_daily_demand: float
    method: str
    environment: Environment


@dataclass(frozen=True)
class RiskResult:
    item_id: str
    location_id: str
    days_of_cover: float | None
    stockout_risk: str
    overstock_risk: str
    estimated_stockout_date: str | None
    environment: Environment


@dataclass(frozen=True)
class RecommendationResult:
    item_id: str
    location_id: str
    reorder_needed: bool
    suggested_reorder_quantity: int
    urgency: str
    supplier_lead_time_days: int
    environment: Environment


@dataclass(frozen=True)
class ConfidenceResult:
    rating: str
    score: float
    reasons: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ExplanationResult:
    summary: str
    drivers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AuditEvent:
    event_id: str
    event_type: str
    actor: str
    timestamp_utc: str
    environment: Environment
    item_id: str | None = None
    location_id: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(cls, event_type: str, actor: str, environment: Environment, item_id: str | None = None, location_id: str | None = None, details: dict[str, Any] | None = None) -> "AuditEvent":
        return cls(
            event_id=str(uuid4()),
            event_type=event_type,
            actor=actor,
            timestamp_utc=datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
            environment=environment,
            item_id=item_id,
            location_id=location_id,
            details=details or {},
        )


@dataclass(frozen=True)
class ForecastSnapshot:
    snapshot_id: str
    created_at_utc: str
    input_summary: dict[str, Any]
    forecast: ForecastResult
    risk: RiskResult
    recommendation: RecommendationResult
    confidence: ConfidenceResult
    explanation: ExplanationResult
    audit_event: AuditEvent

    @classmethod
    def create(cls, input_summary: dict[str, Any], forecast: ForecastResult, risk: RiskResult, recommendation: RecommendationResult, confidence: ConfidenceResult, explanation: ExplanationResult, audit_event: AuditEvent) -> "ForecastSnapshot":
        return cls(
            snapshot_id=str(uuid4()),
            created_at_utc=datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
            input_summary=input_summary,
            forecast=forecast,
            risk=risk,
            recommendation=recommendation,
            confidence=confidence,
            explanation=explanation,
            audit_event=audit_event,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
