from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from invyra_forecasting.constants import Environment


class ForecastSignalType(StrEnum):
    """Standard forecasting signal types produced by Invyra modules."""

    SALE_EVENT = "SALE_EVENT"
    STOCK_MOVEMENT = "STOCK_MOVEMENT"
    RECEIVING_EVENT = "RECEIVING_EVENT"
    PURCHASE_ORDER_EVENT = "PURCHASE_ORDER_EVENT"
    SUPPLIER_LEAD_TIME = "SUPPLIER_LEAD_TIME"
    ADJUSTMENT_EVENT = "ADJUSTMENT_EVENT"
    WASTAGE_EVENT = "WASTAGE_EVENT"
    MARKDOWN_EVENT = "MARKDOWN_EVENT"
    TRANSFER_EVENT = "TRANSFER_EVENT"
    GAP_SCAN_EVENT = "GAP_SCAN_EVENT"
    FLOOR_SCAN_EVENT = "FLOOR_SCAN_EVENT"
    SHELF_EMPTY_EVENT = "SHELF_EMPTY_EVENT"
    LOCATION_STOCK_EVENT = "LOCATION_STOCK_EVENT"


class ForecastSignalDirection(StrEnum):
    """Normalized inventory direction used for forecast interpretation."""

    INBOUND = "INBOUND"
    OUTBOUND = "OUTBOUND"
    NEUTRAL = "NEUTRAL"
    UNKNOWN = "UNKNOWN"


class ForecastSignalSource(StrEnum):
    """Known Invyra module sources that may publish forecasting signals."""

    INVENTORY = "INVENTORY"
    SCANOPS = "SCANOPS"
    REORDER_REVIEW = "REORDER_REVIEW"
    PURCHASING = "PURCHASING"
    RECEIVING = "RECEIVING"
    SUPPLIERS = "SUPPLIERS"
    WASTAGE = "WASTAGE"
    MARKDOWNS = "MARKDOWNS"
    TRANSFERS = "TRANSFERS"
    LOCATIONS = "LOCATIONS"
    POS = "POS"
    DASHBOARD = "DASHBOARD"
    REPORTS = "REPORTS"
    EXTERNAL = "EXTERNAL"


@dataclass(frozen=True)
class ForecastSignal:
    """Normalized, evidence-linked event consumed by the forecasting engine.

    Signals are advisory intelligence inputs only. They do not mutate inventory,
    create stock movements, create purchase orders, or approve purchase orders.
    """

    signal_id: str
    signal_type: ForecastSignalType
    module_source: ForecastSignalSource
    item_id: str
    sku: str
    location_id: str
    timestamp_utc: str
    quantity: float
    unit: str
    direction: ForecastSignalDirection
    reason_code: str | None = None
    confidence: float = 1.0
    evidence_ref: str | None = None
    event_version: str = "1.0"
    environment: Environment = Environment.TRAINING
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        signal_type: ForecastSignalType,
        module_source: ForecastSignalSource,
        item_id: str,
        sku: str,
        location_id: str,
        quantity: float,
        unit: str,
        direction: ForecastSignalDirection,
        reason_code: str | None = None,
        confidence: float = 1.0,
        evidence_ref: str | None = None,
        event_version: str = "1.0",
        environment: Environment = Environment.TRAINING,
        metadata: dict[str, Any] | None = None,
        timestamp_utc: str | None = None,
        signal_id: str | None = None,
    ) -> "ForecastSignal":
        return cls(
            signal_id=signal_id or str(uuid4()),
            signal_type=signal_type,
            module_source=module_source,
            item_id=item_id,
            sku=sku,
            location_id=location_id,
            timestamp_utc=timestamp_utc or datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
            quantity=quantity,
            unit=unit,
            direction=direction,
            reason_code=reason_code,
            confidence=confidence,
            evidence_ref=evidence_ref,
            event_version=event_version,
            environment=environment,
            metadata=metadata or {},
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
