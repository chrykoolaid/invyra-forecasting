from datetime import date

import pytest

from invyra_forecasting.constants import Environment, MovementType
from invyra_forecasting.schemas import StockMovement
from invyra_forecasting.signals import (
    ForecastSignal,
    ForecastSignalDirection,
    ForecastSignalSource,
    ForecastSignalType,
    ForecastSignalValidationError,
    InMemoryForecastSignalRegistry,
    make_location_stock_signal,
    signal_from_stock_movement,
    validate_forecast_signal,
)


def _sale_signal() -> ForecastSignal:
    return ForecastSignal.create(
        signal_type=ForecastSignalType.SALE_EVENT,
        module_source=ForecastSignalSource.POS,
        item_id="ITEM-001",
        sku="SKU-1",
        location_id="LOC-001",
        quantity=4,
        unit="unit",
        direction=ForecastSignalDirection.OUTBOUND,
        reason_code="POS_SALE",
        confidence=0.95,
        evidence_ref="MOV-001",
        environment=Environment.TEST,
    )


def test_registry_accepts_valid_signal():
    registry = InMemoryForecastSignalRegistry()
    signal = registry.publish(_sale_signal())

    assert registry.count() == 1
    assert signal.signal_type == ForecastSignalType.SALE_EVENT
    assert signal.item_id == "ITEM-001"
    assert signal.location_id == "LOC-001"
    assert signal.evidence_ref == "MOV-001"


def test_registry_filters_by_item_location_type_source_and_environment():
    registry = InMemoryForecastSignalRegistry()
    registry.publish(_sale_signal())
    registry.publish(
        ForecastSignal.create(
            signal_type=ForecastSignalType.GAP_SCAN_EVENT,
            module_source=ForecastSignalSource.SCANOPS,
            item_id="ITEM-002",
            sku="SKU-2",
            location_id="LOC-002",
            quantity=0,
            unit="unit",
            direction=ForecastSignalDirection.NEUTRAL,
            confidence=0.8,
            evidence_ref="SCAN-001",
            environment=Environment.TRAINING,
        )
    )

    results = registry.list_signals(
        item_id="ITEM-001",
        location_id="LOC-001",
        signal_type=ForecastSignalType.SALE_EVENT,
        module_source=ForecastSignalSource.POS,
        environment=Environment.TEST,
    )

    assert len(results) == 1
    assert results[0].sku == "SKU-1"


def test_validator_rejects_negative_quantity_and_bad_confidence():
    bad_quantity = ForecastSignal.create(
        signal_type=ForecastSignalType.SALE_EVENT,
        module_source=ForecastSignalSource.POS,
        item_id="ITEM-001",
        sku="SKU-1",
        location_id="LOC-001",
        quantity=-1,
        unit="unit",
        direction=ForecastSignalDirection.OUTBOUND,
    )
    with pytest.raises(ForecastSignalValidationError):
        validate_forecast_signal(bad_quantity)

    bad_confidence = ForecastSignal.create(
        signal_type=ForecastSignalType.SALE_EVENT,
        module_source=ForecastSignalSource.POS,
        item_id="ITEM-001",
        sku="SKU-1",
        location_id="LOC-001",
        quantity=1,
        unit="unit",
        direction=ForecastSignalDirection.OUTBOUND,
        confidence=1.5,
    )
    with pytest.raises(ForecastSignalValidationError):
        validate_forecast_signal(bad_confidence)


def test_stock_movement_normalizer_preserves_ledger_as_evidence_only():
    movement = StockMovement(
        movement_id="MOV-123",
        item_id="ITEM-001",
        location_id="LOC-001",
        movement_date=date(2026, 7, 3),
        movement_type=MovementType.POS_SALE,
        quantity=3,
        environment=Environment.TEST,
    )

    signal = signal_from_stock_movement(movement, sku="SKU-1")

    assert signal.signal_id == "SIG-MOV-123"
    assert signal.signal_type == ForecastSignalType.SALE_EVENT
    assert signal.direction == ForecastSignalDirection.OUTBOUND
    assert signal.evidence_ref == "MOV-123"
    assert signal.metadata["movement_id"] == "MOV-123"
    assert signal.metadata["movement_type"] == "POS_SALE"
    assert movement.quantity == 3


def test_location_stock_signal_is_neutral_snapshot():
    signal = make_location_stock_signal(
        item_id="ITEM-001",
        sku="SKU-1",
        location_id="LOC-001",
        on_hand=22,
        evidence_ref="SNAPSHOT-001",
        environment=Environment.TEST,
    )

    assert signal.signal_type == ForecastSignalType.LOCATION_STOCK_EVENT
    assert signal.direction == ForecastSignalDirection.NEUTRAL
    assert signal.quantity == 22
    assert signal.metadata["on_hand"] == 22
