from __future__ import annotations

from invyra_forecasting.constants import INBOUND_MOVEMENTS, SALES_EQUIVALENT_MOVEMENTS, Environment, MovementType
from invyra_forecasting.schemas import StockMovement
from invyra_forecasting.signals.schema import (
    ForecastSignal,
    ForecastSignalDirection,
    ForecastSignalSource,
    ForecastSignalType,
)


MOVEMENT_SIGNAL_TYPES: dict[MovementType, ForecastSignalType] = {
    MovementType.SALE: ForecastSignalType.SALE_EVENT,
    MovementType.POS_SALE: ForecastSignalType.SALE_EVENT,
    MovementType.WASTAGE: ForecastSignalType.WASTAGE_EVENT,
    MovementType.MARKDOWN_SALE: ForecastSignalType.MARKDOWN_EVENT,
    MovementType.RECEIPT: ForecastSignalType.RECEIVING_EVENT,
    MovementType.TRANSFER_IN: ForecastSignalType.TRANSFER_EVENT,
    MovementType.TRANSFER_OUT: ForecastSignalType.TRANSFER_EVENT,
    MovementType.ADJUSTMENT_IN: ForecastSignalType.ADJUSTMENT_EVENT,
    MovementType.ADJUSTMENT_OUT: ForecastSignalType.ADJUSTMENT_EVENT,
    MovementType.STOCKTAKE_VARIANCE: ForecastSignalType.ADJUSTMENT_EVENT,
    MovementType.GAP_SCAN_CAPTURE: ForecastSignalType.GAP_SCAN_EVENT,
    MovementType.FLOOR_SCAN_CAPTURE: ForecastSignalType.FLOOR_SCAN_EVENT,
}


def direction_from_movement_type(movement_type: MovementType) -> ForecastSignalDirection:
    if movement_type in INBOUND_MOVEMENTS:
        return ForecastSignalDirection.INBOUND
    if movement_type in SALES_EQUIVALENT_MOVEMENTS:
        return ForecastSignalDirection.OUTBOUND
    return ForecastSignalDirection.NEUTRAL


def signal_type_from_movement_type(movement_type: MovementType) -> ForecastSignalType:
    return MOVEMENT_SIGNAL_TYPES.get(movement_type, ForecastSignalType.STOCK_MOVEMENT)


def signal_from_stock_movement(
    movement: StockMovement,
    *,
    sku: str,
    unit: str = "unit",
    module_source: ForecastSignalSource = ForecastSignalSource.INVENTORY,
    evidence_ref: str | None = None,
    confidence: float = 1.0,
    metadata: dict | None = None,
) -> ForecastSignal:
    """Normalize a stock movement into a forecasting signal.

    The movement remains owned by the inventory ledger. The returned signal is a
    read-only intelligence copy for forecast interpretation.
    """

    signal_metadata = {
        "movement_id": movement.movement_id,
        "movement_type": movement.movement_type.value,
    }
    if metadata:
        signal_metadata.update(metadata)

    return ForecastSignal.create(
        signal_type=signal_type_from_movement_type(movement.movement_type),
        module_source=module_source,
        item_id=movement.item_id,
        sku=sku,
        location_id=movement.location_id,
        quantity=movement.quantity,
        unit=unit,
        direction=direction_from_movement_type(movement.movement_type),
        reason_code=movement.movement_type.value,
        confidence=confidence,
        evidence_ref=evidence_ref or movement.movement_id,
        environment=movement.environment,
        metadata=signal_metadata,
        timestamp_utc=f"{movement.movement_date.isoformat()}T00:00:00Z",
        signal_id=f"SIG-{movement.movement_id}",
    )


def make_location_stock_signal(
    *,
    item_id: str,
    sku: str,
    location_id: str,
    on_hand: float,
    unit: str = "unit",
    evidence_ref: str | None = None,
    environment: Environment = Environment.TRAINING,
    confidence: float = 1.0,
) -> ForecastSignal:
    return ForecastSignal.create(
        signal_type=ForecastSignalType.LOCATION_STOCK_EVENT,
        module_source=ForecastSignalSource.INVENTORY,
        item_id=item_id,
        sku=sku,
        location_id=location_id,
        quantity=on_hand,
        unit=unit,
        direction=ForecastSignalDirection.NEUTRAL,
        reason_code="ON_HAND_SNAPSHOT",
        confidence=confidence,
        evidence_ref=evidence_ref,
        environment=environment,
        metadata={"on_hand": on_hand},
    )
