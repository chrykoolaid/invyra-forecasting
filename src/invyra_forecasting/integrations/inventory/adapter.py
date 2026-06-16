from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from invyra_forecasting.api.contracts import (
    ForecastRequest,
    ItemPayload,
    LocationPayload,
    StockMovementPayload,
    StockPositionPayload,
    SupplierProfilePayload,
)
from invyra_forecasting.constants import Environment, MovementType


class InventoryAdapterMappingError(ValueError):
    """Raised when Inventory source data cannot be safely mapped to a forecast request."""


@dataclass(frozen=True)
class InventoryItemRecord:
    item_id: str
    sku: str
    name: str
    category: str
    unit_of_measure: str = "unit"
    minimum_order_quantity: int = 1

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "InventoryItemRecord":
        item_id = _as_required_str(_first(data, "item_id", "id", "inventory_item_id"), "item.item_id")
        sku = _as_optional_str(_first(data, "sku", "barcode", "primary_barcode", default=None)) or item_id
        return cls(
            item_id=item_id,
            sku=sku,
            name=_as_required_str(_first(data, "name", "item_name", "product_name", "description"), "item.name"),
            category=_as_optional_str(_first(data, "category", "category_name", "department", default="Uncategorised")) or "Uncategorised",
            unit_of_measure=_as_optional_str(_first(data, "unit_of_measure", "unit", "uom", default="unit")) or "unit",
            minimum_order_quantity=_as_int(_first(data, "minimum_order_quantity", "minimum_order_qty", "moq", "case_pack", default=1), "item.minimum_order_quantity", minimum=1),
        )


@dataclass(frozen=True)
class InventoryLocationRecord:
    location_id: str
    name: str
    location_type: str = "STORE"

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "InventoryLocationRecord":
        return cls(
            location_id=_as_required_str(_first(data, "location_id", "branch_id", "store_id", "storage_area_id", "id"), "location.location_id"),
            name=_as_required_str(_first(data, "name", "location_name", "branch_name", "store_name", "storage_area_name"), "location.name"),
            location_type=_as_optional_str(_first(data, "location_type", "type", default="STORE")) or "STORE",
        )


@dataclass(frozen=True)
class InventoryStockPositionRecord:
    item_id: str
    location_id: str
    on_hand: float
    reserved: float = 0
    environment: Environment = Environment.TRAINING

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "InventoryStockPositionRecord":
        return cls(
            item_id=_as_required_str(_first(data, "item_id", "inventory_item_id"), "stock_position.item_id"),
            location_id=_as_required_str(_first(data, "location_id", "branch_id", "store_id", "storage_area_id"), "stock_position.location_id"),
            on_hand=_as_float(_first(data, "on_hand", "stock_on_hand", "soh", "quantity_on_hand"), "stock_position.on_hand"),
            reserved=_as_float(_first(data, "reserved", "reserved_stock", "committed", "allocated", default=0), "stock_position.reserved", minimum=0),
            environment=_coerce_environment(_first(data, "environment", "env", default=Environment.TRAINING)),
        )


@dataclass(frozen=True)
class InventoryMovementLedgerRecord:
    movement_id: str
    item_id: str
    location_id: str
    movement_date: date
    movement_type: MovementType
    quantity: float
    environment: Environment = Environment.TRAINING

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "InventoryMovementLedgerRecord":
        movement_type = _coerce_movement_type(_first(data, "movement_type", "type", "reason", "source"))
        raw_quantity = _as_float(_first(data, "quantity", "qty", "movement_qty", "delta_quantity"), "movement.quantity")
        return cls(
            movement_id=_as_required_str(_first(data, "movement_id", "ledger_id", "id"), "movement.movement_id"),
            item_id=_as_required_str(_first(data, "item_id", "inventory_item_id"), "movement.item_id"),
            location_id=_as_required_str(_first(data, "location_id", "branch_id", "store_id", "storage_area_id"), "movement.location_id"),
            movement_date=_coerce_date(_first(data, "movement_date", "date", "created_at", "timestamp"), "movement.movement_date"),
            movement_type=movement_type,
            quantity=abs(raw_quantity),
            environment=_coerce_environment(_first(data, "environment", "env", default=Environment.TRAINING)),
        )


@dataclass(frozen=True)
class InventorySupplierProfileRecord:
    supplier_id: str
    item_id: str
    lead_time_days: int
    lead_time_variability_days: int = 0
    minimum_order_quantity: int = 1

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "InventorySupplierProfileRecord":
        return cls(
            supplier_id=_as_required_str(_first(data, "supplier_id", "primary_supplier_id", "id"), "supplier_profile.supplier_id"),
            item_id=_as_required_str(_first(data, "item_id", "inventory_item_id"), "supplier_profile.item_id"),
            lead_time_days=_as_int(_first(data, "lead_time_days", "lead_time", "supplier_lead_time_days", default=0), "supplier_profile.lead_time_days", minimum=0),
            lead_time_variability_days=_as_int(_first(data, "lead_time_variability_days", "lead_time_variability", default=0), "supplier_profile.lead_time_variability_days", minimum=0),
            minimum_order_quantity=_as_int(_first(data, "minimum_order_quantity", "minimum_order_qty", "moq", "case_pack", default=1), "supplier_profile.minimum_order_quantity", minimum=1),
        )


@dataclass(frozen=True)
class InventoryForecastMappingInput:
    item: InventoryItemRecord
    location: InventoryLocationRecord
    stock_position: InventoryStockPositionRecord
    movements: Sequence[InventoryMovementLedgerRecord]
    supplier_profile: InventorySupplierProfileRecord
    environment: Environment = Environment.TRAINING
    actor: str = "inventory_adapter"
    forecast_horizon_days: int = 30
    demand_lookback_days: int = 30
    target_cover_days: int = 14
    safety_stock_days: int = 3
    anchor_date: date | None = None
    write_snapshot: bool = False

    @classmethod
    def from_mappings(
        cls,
        *,
        item: Mapping[str, Any],
        location: Mapping[str, Any],
        stock_position: Mapping[str, Any],
        movements: Sequence[Mapping[str, Any]],
        supplier_profile: Mapping[str, Any],
        environment: Environment | str = Environment.TRAINING,
        actor: str = "inventory_adapter",
        forecast_horizon_days: int = 30,
        demand_lookback_days: int = 30,
        target_cover_days: int = 14,
        safety_stock_days: int = 3,
        anchor_date: date | str | None = None,
        write_snapshot: bool = False,
    ) -> "InventoryForecastMappingInput":
        return cls(
            item=InventoryItemRecord.from_mapping(item),
            location=InventoryLocationRecord.from_mapping(location),
            stock_position=InventoryStockPositionRecord.from_mapping(stock_position),
            movements=[InventoryMovementLedgerRecord.from_mapping(movement) for movement in movements],
            supplier_profile=InventorySupplierProfileRecord.from_mapping(supplier_profile),
            environment=_coerce_environment(environment),
            actor=actor,
            forecast_horizon_days=forecast_horizon_days,
            demand_lookback_days=demand_lookback_days,
            target_cover_days=target_cover_days,
            safety_stock_days=safety_stock_days,
            anchor_date=_coerce_date(anchor_date, "anchor_date") if anchor_date is not None else None,
            write_snapshot=write_snapshot,
        )


class InventoryForecastMapper:
    """Read-only mapper from Inventory records to the forecasting API request contract."""

    def map_to_forecast_request(self, source: InventoryForecastMappingInput) -> ForecastRequest:
        environment = _coerce_environment(source.environment)
        self._validate_relationships(source, environment)
        return ForecastRequest(
            actor=source.actor,
            environment=environment,
            forecast_horizon_days=source.forecast_horizon_days,
            demand_lookback_days=source.demand_lookback_days,
            target_cover_days=source.target_cover_days,
            safety_stock_days=source.safety_stock_days,
            anchor_date=source.anchor_date,
            write_snapshot=source.write_snapshot,
            item=ItemPayload(
                item_id=source.item.item_id,
                sku=source.item.sku or source.item.item_id,
                name=source.item.name,
                category=source.item.category,
                unit_of_measure=source.item.unit_of_measure,
                minimum_order_quantity=source.item.minimum_order_quantity,
            ),
            location=LocationPayload(
                location_id=source.location.location_id,
                name=source.location.name,
                location_type=source.location.location_type,
            ),
            stock_position=StockPositionPayload(
                item_id=source.stock_position.item_id,
                location_id=source.stock_position.location_id,
                on_hand=source.stock_position.on_hand,
                reserved=source.stock_position.reserved,
                environment=source.stock_position.environment,
            ),
            movements=[
                StockMovementPayload(
                    movement_id=movement.movement_id,
                    item_id=movement.item_id,
                    location_id=movement.location_id,
                    movement_date=movement.movement_date,
                    movement_type=movement.movement_type,
                    quantity=movement.quantity,
                    environment=movement.environment,
                )
                for movement in source.movements
            ],
            supplier_profile=SupplierProfilePayload(
                supplier_id=source.supplier_profile.supplier_id,
                item_id=source.supplier_profile.item_id,
                lead_time_days=source.supplier_profile.lead_time_days,
                lead_time_variability_days=source.supplier_profile.lead_time_variability_days,
                minimum_order_quantity=source.supplier_profile.minimum_order_quantity,
            ),
        )

    def _validate_relationships(self, source: InventoryForecastMappingInput, environment: Environment) -> None:
        if source.stock_position.item_id != source.item.item_id:
            raise InventoryAdapterMappingError("stock_position item_id does not match item")
        if source.stock_position.location_id != source.location.location_id:
            raise InventoryAdapterMappingError("stock_position location_id does not match location")
        if source.stock_position.environment != environment:
            raise InventoryAdapterMappingError(f"stock_position environment mismatch: expected {environment.value}, got {source.stock_position.environment.value}")
        if source.supplier_profile.item_id != source.item.item_id:
            raise InventoryAdapterMappingError("supplier_profile item_id does not match item")
        for movement in source.movements:
            if movement.item_id != source.item.item_id:
                raise InventoryAdapterMappingError(f"movement {movement.movement_id} item_id does not match item")
            if movement.location_id != source.location.location_id:
                raise InventoryAdapterMappingError(f"movement {movement.movement_id} location_id does not match location")
            if movement.environment != environment:
                raise InventoryAdapterMappingError(f"movement {movement.movement_id} environment mismatch: expected {environment.value}, got {movement.environment.value}")


def map_inventory_to_forecast_request(source: InventoryForecastMappingInput) -> ForecastRequest:
    return InventoryForecastMapper().map_to_forecast_request(source)


def _first(data: Mapping[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in data and data[key] is not None:
            return data[key]
    return default


def _as_required_str(value: Any, field_name: str) -> str:
    text = _as_optional_str(value)
    if not text:
        raise InventoryAdapterMappingError(f"{field_name} is required")
    return text


def _as_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _as_float(value: Any, field_name: str, minimum: float | None = None) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise InventoryAdapterMappingError(f"{field_name} must be numeric") from exc
    if minimum is not None and number < minimum:
        raise InventoryAdapterMappingError(f"{field_name} must be at least {minimum:g}")
    return number


def _as_int(value: Any, field_name: str, minimum: int | None = None) -> int:
    number = _as_float(value, field_name, minimum=minimum)
    if number % 1 != 0:
        raise InventoryAdapterMappingError(f"{field_name} must be a whole number")
    return int(number)


def _coerce_environment(value: Environment | str) -> Environment:
    if isinstance(value, Environment):
        return value
    normalized = str(value).strip().upper()
    try:
        return Environment(normalized)
    except ValueError as exc:
        raise InventoryAdapterMappingError(f"Unsupported environment: {value}") from exc


def _coerce_movement_type(value: MovementType | str) -> MovementType:
    if isinstance(value, MovementType):
        return value
    normalized = str(value).strip().upper().replace("-", "_").replace(" ", "_")
    aliases = {
        "SALE": MovementType.SALE,
        "POS": MovementType.POS_SALE,
        "POS_SALE": MovementType.POS_SALE,
        "POS_AUTO_DEDUCTION": MovementType.POS_SALE,
        "WASTE": MovementType.WASTAGE,
        "WASTAGE": MovementType.WASTAGE,
        "MARKDOWN": MovementType.MARKDOWN_SALE,
        "MARKDOWN_SALE": MovementType.MARKDOWN_SALE,
        "RECEIVING": MovementType.RECEIPT,
        "RECEIPT": MovementType.RECEIPT,
        "DELIVERY_RECEIPT": MovementType.RECEIPT,
        "TRANSFER_IN": MovementType.TRANSFER_IN,
        "TRANSFER_OUT": MovementType.TRANSFER_OUT,
        "ADJUSTMENT_IN": MovementType.ADJUSTMENT_IN,
        "ADJUSTMENT_OUT": MovementType.ADJUSTMENT_OUT,
        "STOCKTAKE": MovementType.STOCKTAKE_VARIANCE,
        "STOCKTAKE_VARIANCE": MovementType.STOCKTAKE_VARIANCE,
        "GAP_SCAN": MovementType.GAP_SCAN_CAPTURE,
        "GAP_SCAN_CAPTURE": MovementType.GAP_SCAN_CAPTURE,
        "FLOOR_SCAN": MovementType.FLOOR_SCAN_CAPTURE,
        "FLOOR_SCAN_CAPTURE": MovementType.FLOOR_SCAN_CAPTURE,
    }
    if normalized in aliases:
        return aliases[normalized]
    try:
        return MovementType(normalized)
    except ValueError as exc:
        raise InventoryAdapterMappingError(f"Unsupported movement_type: {value}") from exc


def _coerce_date(value: date | datetime | str, field_name: str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    try:
        return date.fromisoformat(text[:10])
    except ValueError as exc:
        raise InventoryAdapterMappingError(f"{field_name} must be an ISO date") from exc
