import json
from pathlib import Path

import pytest

from invyra_forecasting.constants import Environment, MovementType
from invyra_forecasting.data.validation import validate_forecast_input
from invyra_forecasting.integrations.inventory import (
    InventoryAdapterMappingError,
    InventoryForecastMapper,
    InventoryForecastMappingInput,
)

FIXTURE_PATH = Path(__file__).parents[1] / "integrations" / "inventory" / "fixtures" / "phase2a_item_details_source.json"


def _payload() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _source(payload: dict | None = None) -> InventoryForecastMappingInput:
    data = payload or _payload()
    return InventoryForecastMappingInput.from_mappings(
        item=data["item"],
        location=data["location"],
        stock_position=data["stock_position"],
        movements=data["movements"],
        supplier_profile=data["supplier_profile"],
        environment=data["environment"],
        actor=data["actor"],
        anchor_date=data["anchor_date"],
    )


def test_inventory_adapter_maps_real_item_details_fixture_to_forecast_request():
    request = InventoryForecastMapper().map_to_forecast_request(_source())

    assert request.actor == "item_details_panel"
    assert request.environment == Environment.TRAINING
    assert request.write_snapshot is False
    assert request.item.item_id == "ITEM-001"
    assert request.item.sku == "SKU-COFFEE-250G"
    assert request.item.minimum_order_quantity == 6
    assert request.location.location_id == "BRANCH-001"
    assert request.location.location_type == "BRANCH"
    assert request.stock_position.on_hand == 18
    assert request.stock_position.reserved == 2
    assert request.stock_position.environment == Environment.TRAINING
    assert request.movements[0].movement_type == MovementType.POS_SALE
    assert request.movements[0].quantity == 3
    assert request.movements[1].movement_type == MovementType.RECEIPT
    assert request.supplier_profile.lead_time_days == 5
    assert request.supplier_profile.minimum_order_quantity == 6

    bundle = request.to_bundle()
    validate_forecast_input(bundle)
    assert bundle.stock_position.available == 16


def test_inventory_adapter_rejects_cross_environment_stock_position():
    payload = _payload()
    payload["stock_position"]["environment"] = "LIVE"

    with pytest.raises(InventoryAdapterMappingError, match="stock_position environment mismatch"):
        InventoryForecastMapper().map_to_forecast_request(_source(payload))


def test_inventory_adapter_rejects_cross_environment_movement():
    payload = _payload()
    payload["movements"][0]["environment"] = "LIVE"

    with pytest.raises(InventoryAdapterMappingError, match="movement MOV-001 environment mismatch"):
        InventoryForecastMapper().map_to_forecast_request(_source(payload))


def test_inventory_adapter_rejects_movement_for_different_item():
    payload = _payload()
    payload["movements"][0]["item_id"] = "ITEM-OTHER"

    with pytest.raises(InventoryAdapterMappingError, match="movement MOV-001 item_id does not match item"):
        InventoryForecastMapper().map_to_forecast_request(_source(payload))


def test_inventory_adapter_rejects_unsupported_movement_type():
    payload = _payload()
    payload["movements"][0]["source"] = "UNKNOWN_LEDGER_ACTION"

    with pytest.raises(InventoryAdapterMappingError, match="Unsupported movement_type"):
        _source(payload)
