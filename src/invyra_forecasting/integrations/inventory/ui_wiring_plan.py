from __future__ import annotations

from copy import deepcopy
from typing import Any

REQUIRED_COMPONENT = "InventoryItemDetailsForecastPanel"
REQUIRED_PANEL_LOCATION = "Inventory Item Details"
REQUIRED_DATA_SOURCE = "POST /inventory/item-details/forecast"
REQUIRED_SNAPSHOT_SOURCE = "GET /inventory/item-details/forecast/snapshots/{snapshot_id}"
REQUIRED_VIEW_MODEL_BUILDER = "build_item_details_forecast_view_model"

REQUIRED_STATES = ["available", "low_confidence", "unavailable"]
REQUIRED_DISPLAY_FIELDS = [
    "forecast_demand_next_30_days",
    "average_daily_demand",
    "days_of_cover",
    "stockout_risk",
    "overstock_risk",
    "suggested_reorder_quantity",
    "confidence_rating",
    "short_explanation",
]

FORBIDDEN_DUPLICATIONS = [
    "Stock History",
    "Reorder Review",
    "Dashboard Priority Issues",
    "Movement Ledger",
    "Purchase Order Approval",
]

FORBIDDEN_ACTIONS = [
    "mutate_stock",
    "create_purchase_order",
    "approve_purchase_order",
    "auto_reorder",
    "hide_low_confidence_forecast",
    "block_item_details_on_forecast_failure",
]

ITEM_DETAILS_UI_WIRING_PLAN: dict[str, Any] = {
    "phase": "Phase 2F",
    "status": "planning_guard_only",
    "component": REQUIRED_COMPONENT,
    "panel_location": REQUIRED_PANEL_LOCATION,
    "placement": {
        "recommended_area": "Item Details intelligence section",
        "layout": "compact_panel",
        "collapsible": True,
        "blocks_existing_item_details": False,
        "duplicates_existing_sections": False,
    },
    "data_sources": {
        "panel_endpoint": REQUIRED_DATA_SOURCE,
        "snapshot_endpoint": REQUIRED_SNAPSHOT_SOURCE,
        "view_model_builder": REQUIRED_VIEW_MODEL_BUILDER,
    },
    "states": {
        "available": {
            "render_fields": REQUIRED_DISPLAY_FIELDS,
            "show_snapshot_link": True,
            "show_warnings": True,
            "keep_item_details_usable": True,
            "keep_stock_history_usable": True,
        },
        "low_confidence": {
            "render_fields": REQUIRED_DISPLAY_FIELDS,
            "show_snapshot_link": True,
            "show_warnings": True,
            "warning_message": "Low confidence forecast. Verify movement history, stock accuracy, and supplier lead time before acting.",
            "keep_item_details_usable": True,
            "keep_stock_history_usable": True,
        },
        "unavailable": {
            "render_fields": [],
            "show_snapshot_link": False,
            "show_warnings": True,
            "message": "Forecast unavailable. Item Details and stock history remain usable.",
            "keep_item_details_usable": True,
            "keep_stock_history_usable": True,
        },
    },
    "must_preserve": {
        "item_details_usable": True,
        "stock_history_usable": True,
        "manual_review_available": True,
        "inventory_ledger_source_of_truth": True,
        "environment_separation": True,
        "low_confidence_visible": True,
        "snapshot_evidence_optional": True,
    },
    "must_not_do": {
        "mutate_stock": False,
        "create_purchase_order": False,
        "approve_purchase_order": False,
        "auto_reorder": False,
        "hide_low_confidence_forecast": False,
        "block_item_details_on_forecast_failure": False,
        "duplicate_stock_history": False,
        "duplicate_reorder_review": False,
        "show_raw_model_internals": False,
        "show_raw_movement_rows": False,
    },
    "forbidden_duplications": FORBIDDEN_DUPLICATIONS,
    "forbidden_actions": FORBIDDEN_ACTIONS,
    "guard_tests_required_before_ui_wiring": True,
}


class ItemDetailsUIWiringPlanError(ValueError):
    """Raised when a proposed Item Details UI wiring plan violates locked guardrails."""


def get_item_details_ui_wiring_plan() -> dict[str, Any]:
    return deepcopy(ITEM_DETAILS_UI_WIRING_PLAN)


def validate_item_details_ui_wiring_plan(plan: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if plan.get("component") != REQUIRED_COMPONENT:
        errors.append("component must be InventoryItemDetailsForecastPanel")
    if plan.get("panel_location") != REQUIRED_PANEL_LOCATION:
        errors.append("panel_location must be Inventory Item Details")
    placement = plan.get("placement") or {}
    if placement.get("blocks_existing_item_details") is not False:
        errors.append("forecast panel must not block existing Item Details")
    if placement.get("duplicates_existing_sections") is not False:
        errors.append("forecast panel must not duplicate existing Item Details sections")
    data_sources = plan.get("data_sources") or {}
    if data_sources.get("panel_endpoint") != REQUIRED_DATA_SOURCE:
        errors.append("panel endpoint must remain POST /inventory/item-details/forecast")
    if data_sources.get("snapshot_endpoint") != REQUIRED_SNAPSHOT_SOURCE:
        errors.append("snapshot endpoint must remain the Item Details snapshot evidence endpoint")
    if data_sources.get("view_model_builder") != REQUIRED_VIEW_MODEL_BUILDER:
        errors.append("view model builder must remain build_item_details_forecast_view_model")
    states = plan.get("states") or {}
    for state in REQUIRED_STATES:
        if state not in states:
            errors.append(f"missing required state: {state}")
            continue
        state_plan = states[state]
        if state in {"available", "low_confidence"} and state_plan.get("render_fields") != REQUIRED_DISPLAY_FIELDS:
            errors.append(f"{state} render_fields must match the locked view-model field order")
        if state == "unavailable" and state_plan.get("render_fields") != []:
            errors.append("unavailable state must not render forecast fields")
        if state_plan.get("keep_item_details_usable") is not True:
            errors.append(f"{state} must keep Item Details usable")
        if state_plan.get("keep_stock_history_usable") is not True:
            errors.append(f"{state} must keep Stock History usable")
    must_preserve = plan.get("must_preserve") or {}
    for key in ["item_details_usable", "stock_history_usable", "manual_review_available", "inventory_ledger_source_of_truth", "environment_separation", "low_confidence_visible"]:
        if must_preserve.get(key) is not True:
            errors.append(f"must_preserve.{key} must be true")
    must_not_do = plan.get("must_not_do") or {}
    for key in ["mutate_stock", "create_purchase_order", "approve_purchase_order", "auto_reorder", "hide_low_confidence_forecast", "block_item_details_on_forecast_failure", "duplicate_stock_history", "duplicate_reorder_review", "show_raw_model_internals", "show_raw_movement_rows"]:
        if must_not_do.get(key) is not False:
            errors.append(f"must_not_do.{key} must be false")
    forbidden_duplications = set(plan.get("forbidden_duplications") or [])
    for item in FORBIDDEN_DUPLICATIONS:
        if item not in forbidden_duplications:
            errors.append(f"forbidden_duplications must include {item}")
    forbidden_actions = set(plan.get("forbidden_actions") or [])
    for item in FORBIDDEN_ACTIONS:
        if item not in forbidden_actions:
            errors.append(f"forbidden_actions must include {item}")
    if plan.get("guard_tests_required_before_ui_wiring") is not True:
        errors.append("guard_tests_required_before_ui_wiring must be true")
    return errors


def assert_valid_item_details_ui_wiring_plan(plan: dict[str, Any]) -> None:
    errors = validate_item_details_ui_wiring_plan(plan)
    if errors:
        raise ItemDetailsUIWiringPlanError("; ".join(errors))
