from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field

from invyra_forecasting.constants import Environment, MovementType
from invyra_forecasting.schemas import ForecastInputBundle, Item, Location, StockMovement, StockPosition, SupplierProfile


class ItemPayload(BaseModel):
    item_id: str
    sku: str
    name: str
    category: str
    unit_of_measure: str = "unit"
    minimum_order_quantity: int = Field(default=1, ge=1)

    def to_entity(self) -> Item:
        return Item(self.item_id, self.sku, self.name, self.category, self.unit_of_measure, self.minimum_order_quantity)


class LocationPayload(BaseModel):
    location_id: str
    name: str
    location_type: str = "STORE"

    def to_entity(self) -> Location:
        return Location(self.location_id, self.name, self.location_type)


class StockPositionPayload(BaseModel):
    item_id: str
    location_id: str
    on_hand: float
    reserved: float = Field(default=0, ge=0)
    environment: Environment = Environment.TRAINING

    def to_entity(self) -> StockPosition:
        return StockPosition(self.item_id, self.location_id, self.on_hand, self.reserved, self.environment)


class StockMovementPayload(BaseModel):
    movement_id: str
    item_id: str
    location_id: str
    movement_date: date
    movement_type: MovementType
    quantity: float = Field(ge=0)
    environment: Environment = Environment.TRAINING

    def to_entity(self) -> StockMovement:
        return StockMovement(self.movement_id, self.item_id, self.location_id, self.movement_date, self.movement_type, self.quantity, self.environment)


class SupplierProfilePayload(BaseModel):
    supplier_id: str
    item_id: str
    lead_time_days: int = Field(ge=0)
    lead_time_variability_days: int = Field(default=0, ge=0)
    minimum_order_quantity: int = Field(default=1, ge=1)

    def to_entity(self) -> SupplierProfile:
        return SupplierProfile(self.supplier_id, self.item_id, self.lead_time_days, self.lead_time_variability_days, self.minimum_order_quantity)


class ForecastRequest(BaseModel):
    actor: str = "api"
    environment: Environment = Environment.TRAINING
    forecast_horizon_days: int = Field(default=30, ge=1, le=365)
    demand_lookback_days: int = Field(default=30, ge=1, le=730)
    target_cover_days: int = Field(default=14, ge=1, le=365)
    safety_stock_days: int = Field(default=3, ge=0, le=90)
    anchor_date: date | None = None
    write_snapshot: bool = False
    item: ItemPayload
    location: LocationPayload
    stock_position: StockPositionPayload
    movements: list[StockMovementPayload] = Field(default_factory=list)
    supplier_profile: SupplierProfilePayload

    def to_bundle(self) -> ForecastInputBundle:
        return ForecastInputBundle(
            item=self.item.to_entity(),
            location=self.location.to_entity(),
            stock_position=self.stock_position.to_entity(),
            movements=[movement.to_entity() for movement in self.movements],
            supplier_profile=self.supplier_profile.to_entity(),
            environment=self.environment,
        )


class BatchForecastRequest(BaseModel):
    actor: str = "api_batch"
    write_snapshots: bool = False
    requests: list[ForecastRequest] = Field(default_factory=list)


class OverrideAuditRequest(BaseModel):
    actor: str
    environment: Environment
    item_id: str
    location_id: str
    original_recommendation: dict[str, Any]
    override_action: str
    reason: str
