from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field

from invyra_forecasting.constants import Environment


class ItemDetailsForecastPanelRequest(BaseModel):
    """Inventory-owned payload for the Item Details forecast panel endpoint.

    The fields intentionally mirror Inventory source records rather than exposing engine
    internals. The API layer maps this payload through the Phase 2A adapter and Phase 2B
    panel boundary.
    """

    actor: str = "item_details_panel"
    environment: Environment = Environment.TRAINING
    persist_snapshot: bool = True
    forecast_horizon_days: int = Field(default=30, ge=1, le=365)
    demand_lookback_days: int = Field(default=30, ge=1, le=730)
    target_cover_days: int = Field(default=14, ge=1, le=365)
    safety_stock_days: int = Field(default=3, ge=0, le=90)
    anchor_date: date | None = None
    item: dict[str, Any]
    location: dict[str, Any]
    stock_position: dict[str, Any]
    movements: list[dict[str, Any]] = Field(default_factory=list)
    supplier_profile: dict[str, Any]

    def boundary_options(self) -> dict[str, Any]:
        return {
            "forecast_horizon_days": self.forecast_horizon_days,
            "demand_lookback_days": self.demand_lookback_days,
            "target_cover_days": self.target_cover_days,
            "safety_stock_days": self.safety_stock_days,
            "anchor_date": self.anchor_date,
        }
