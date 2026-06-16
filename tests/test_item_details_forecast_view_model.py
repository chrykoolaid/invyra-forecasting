import json
from pathlib import Path

import pytest

from invyra_forecasting.integrations.inventory.view_model import (
    COMPONENT_NAME,
    LOW_CONFIDENCE_MESSAGE,
    ItemDetailsForecastViewModelBuilder,
    ItemDetailsForecastViewModelError,
    build_item_details_forecast_view_model,
)

EXAMPLES_DIR = Path(__file__).parents[1] / "examples" / "api" / "inventory_item_details"


def _load_json(filename: str) -> dict:
    return json.loads((EXAMPLES_DIR / filename).read_text(encoding="utf-8"))


def _field_by_key(view_model: dict, key: str) -> dict:
    for field in view_model["fields"]:
        if field["key"] == key:
            return field
    raise AssertionError(f"Missing field: {key}")


def _assert_common_guardrails(view_model: dict) -> None:
    guardrails = view_model["guardrails"]
    assert guardrails["advisory_only"] is True
    assert guardrails["inventory_ledger_source_of_truth"] is True
    assert guardrails["mutates_stock"] is False
    assert guardrails["creates_purchase_order"] is False
    assert guardrails["approves_purchase_order"] is False
    assert view_model["actions"]["create_purchase_order_visible"] is False
    assert view_model["actions"]["approve_purchase_order_visible"] is False
    assert view_model["actions"]["stock_adjustment_visible"] is False
    assert view_model["rendering_rules"]["show_raw_model_internals"] is False
    assert view_model["rendering_rules"]["show_raw_movement_rows"] is False
    assert view_model["rendering_rules"]["duplicate_stock_history"] is False
    assert view_model["rendering_rules"]["duplicate_reorder_review"] is False
    assert view_model["rendering_rules"]["block_item_details_on_forecast_failure"] is False


def test_view_model_builds_clean_available_contract_from_panel_response():
    panel = _load_json("item_details_forecast_response_available.json")

    view_model = build_item_details_forecast_view_model(panel)

    assert view_model["component"] == COMPONENT_NAME
    assert view_model["status"] == "available"
    assert view_model["title"] == "Forecast intelligence"
    assert view_model["status_chip"]["label"] == "Medium"
    assert view_model["status_chip"]["tone"] == "warning"
    assert view_model["snapshot"]["available"] is True
    assert view_model["snapshot"]["snapshot_id"] == panel["snapshot_id"]
    assert view_model["actions"]["view_snapshot_visible"] is True
    assert [field["key"] for field in view_model["fields"]] == [
        "forecast_demand_next_30_days",
        "average_daily_demand",
        "days_of_cover",
        "stockout_risk",
        "overstock_risk",
        "suggested_reorder_quantity",
        "confidence_rating",
        "short_explanation",
    ]
    assert _field_by_key(view_model, "forecast_demand_next_30_days")["label"] == "Forecast demand next 30 days"
    assert _field_by_key(view_model, "suggested_reorder_quantity")["helper"].startswith("Advisory quantity only")
    assert "confidence_score" not in [field["key"] for field in view_model["fields"]]
    _assert_common_guardrails(view_model)


def test_view_model_keeps_low_confidence_visible_with_warning():
    panel = _load_json("item_details_forecast_response_low_confidence.json")

    view_model = ItemDetailsForecastViewModelBuilder().build(panel)

    assert view_model["status"] == "low_confidence"
    assert view_model["status_chip"] == {"label": "Low confidence", "tone": "warning"}
    assert view_model["fields"]
    assert LOW_CONFIDENCE_MESSAGE in view_model["warnings"]
    assert _field_by_key(view_model, "confidence_rating")["chip"] == {"label": "Low", "tone": "warning"}
    assert view_model["fallback"]["manual_review_available"] is True
    _assert_common_guardrails(view_model)


def test_view_model_builds_safe_unavailable_contract():
    panel = _load_json("item_details_forecast_response_unavailable.json")

    view_model = build_item_details_forecast_view_model(panel)

    assert view_model["status"] == "unavailable"
    assert view_model["title"] == "Forecast unavailable"
    assert view_model["fields"] == []
    assert view_model["snapshot"] == {
        "available": False,
        "snapshot_id": None,
        "label": "No forecast evidence available",
        "generated_at_utc": None,
    }
    assert view_model["actions"]["view_snapshot_visible"] is False
    assert view_model["fallback"]["item_details_usable"] is True
    assert view_model["fallback"]["stock_history_usable"] is True
    _assert_common_guardrails(view_model)


def test_view_model_rejects_unknown_panel_status():
    with pytest.raises(ItemDetailsForecastViewModelError, match="Unsupported panel status"):
        build_item_details_forecast_view_model({"status": "debug_mode"})


def test_view_model_risk_chip_rules_are_stable():
    panel = _load_json("item_details_forecast_response_available.json")
    panel["display_fields"]["stockout_risk"] = "High"
    panel["display_fields"]["overstock_risk"] = "Low"

    view_model = build_item_details_forecast_view_model(panel)

    assert _field_by_key(view_model, "stockout_risk")["chip"] == {"label": "High", "tone": "danger"}
    assert _field_by_key(view_model, "stockout_risk")["emphasis"] == "high"
    assert _field_by_key(view_model, "overstock_risk")["chip"] == {"label": "Low", "tone": "success"}
