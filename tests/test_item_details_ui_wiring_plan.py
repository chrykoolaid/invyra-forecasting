import copy

import pytest

from invyra_forecasting.integrations.inventory.ui_wiring_plan import (
    REQUIRED_DISPLAY_FIELDS,
    ItemDetailsUIWiringPlanError,
    assert_valid_item_details_ui_wiring_plan,
    get_item_details_ui_wiring_plan,
    validate_item_details_ui_wiring_plan,
)


def _plan() -> dict:
    return get_item_details_ui_wiring_plan()


def test_locked_item_details_ui_wiring_plan_is_valid():
    plan = _plan()

    assert validate_item_details_ui_wiring_plan(plan) == []
    assert_valid_item_details_ui_wiring_plan(plan)
    assert plan["status"] == "planning_guard_only"
    assert plan["component"] == "InventoryItemDetailsForecastPanel"
    assert plan["panel_location"] == "Inventory Item Details"
    assert plan["data_sources"]["panel_endpoint"] == "POST /inventory/item-details/forecast"
    assert plan["data_sources"]["snapshot_endpoint"] == "GET /inventory/item-details/forecast/snapshots/{snapshot_id}"
    assert plan["data_sources"]["view_model_builder"] == "build_item_details_forecast_view_model"


def test_wiring_plan_locks_clean_field_order_for_visible_states():
    plan = _plan()

    assert plan["states"]["available"]["render_fields"] == REQUIRED_DISPLAY_FIELDS
    assert plan["states"]["low_confidence"]["render_fields"] == REQUIRED_DISPLAY_FIELDS
    assert plan["states"]["unavailable"]["render_fields"] == []
    assert plan["states"]["low_confidence"]["show_warnings"] is True
    assert "Verify movement history" in plan["states"]["low_confidence"]["warning_message"]


def test_wiring_plan_preserves_existing_item_details_and_stock_history():
    plan = _plan()

    assert plan["placement"]["blocks_existing_item_details"] is False
    assert plan["placement"]["duplicates_existing_sections"] is False
    assert plan["must_preserve"]["item_details_usable"] is True
    assert plan["must_preserve"]["stock_history_usable"] is True
    assert plan["must_preserve"]["manual_review_available"] is True
    assert plan["states"]["unavailable"]["keep_item_details_usable"] is True
    assert plan["states"]["unavailable"]["keep_stock_history_usable"] is True


def test_wiring_plan_blocks_purchase_and_stock_mutation_actions():
    plan = _plan()

    assert plan["must_not_do"]["mutate_stock"] is False
    assert plan["must_not_do"]["create_purchase_order"] is False
    assert plan["must_not_do"]["approve_purchase_order"] is False
    assert plan["must_not_do"]["auto_reorder"] is False
    assert "mutate_stock" in plan["forbidden_actions"]
    assert "create_purchase_order" in plan["forbidden_actions"]
    assert "approve_purchase_order" in plan["forbidden_actions"]


def test_wiring_plan_blocks_duplicate_modules():
    plan = _plan()

    assert plan["must_not_do"]["duplicate_stock_history"] is False
    assert plan["must_not_do"]["duplicate_reorder_review"] is False
    assert "Stock History" in plan["forbidden_duplications"]
    assert "Reorder Review" in plan["forbidden_duplications"]
    assert "Movement Ledger" in plan["forbidden_duplications"]


def test_wiring_plan_rejects_blocking_item_details_on_failure():
    plan = _plan()
    plan["states"]["unavailable"]["keep_item_details_usable"] = False

    errors = validate_item_details_ui_wiring_plan(plan)

    assert "unavailable must keep Item Details usable" in errors
    with pytest.raises(ItemDetailsUIWiringPlanError):
        assert_valid_item_details_ui_wiring_plan(plan)


def test_wiring_plan_rejects_hidden_low_confidence_forecast():
    plan = _plan()
    plan["must_preserve"]["low_confidence_visible"] = False

    errors = validate_item_details_ui_wiring_plan(plan)

    assert "must_preserve.low_confidence_visible must be true" in errors


def test_wiring_plan_rejects_wrong_field_order():
    plan = _plan()
    bad_fields = copy.deepcopy(REQUIRED_DISPLAY_FIELDS)
    bad_fields.reverse()
    plan["states"]["available"]["render_fields"] = bad_fields

    errors = validate_item_details_ui_wiring_plan(plan)

    assert "available render_fields must match the locked view-model field order" in errors


def test_wiring_plan_rejects_po_or_stock_actions():
    plan = _plan()
    plan["must_not_do"]["create_purchase_order"] = True
    plan["must_not_do"]["mutate_stock"] = True

    errors = validate_item_details_ui_wiring_plan(plan)

    assert "must_not_do.create_purchase_order must be false" in errors
    assert "must_not_do.mutate_stock must be false" in errors


def test_wiring_plan_returns_a_copy_not_mutable_global_state():
    plan = _plan()
    plan["component"] = "UnsafeComponent"

    fresh_plan = _plan()

    assert fresh_plan["component"] == "InventoryItemDetailsForecastPanel"
    assert validate_item_details_ui_wiring_plan(fresh_plan) == []
