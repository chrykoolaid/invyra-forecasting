import json
from pathlib import Path

from invyra_forecasting.integrations.inventory.view_model import build_item_details_forecast_view_model

EXAMPLES_DIR = Path(__file__).parents[1] / "examples" / "api" / "inventory_item_details"


def _load_json(filename: str) -> dict:
    return json.loads((EXAMPLES_DIR / filename).read_text(encoding="utf-8"))


def _assert_view_model_guardrails(view_model: dict) -> None:
    assert view_model["guardrails"]["advisory_only"] is True
    assert view_model["guardrails"]["inventory_ledger_source_of_truth"] is True
    assert view_model["guardrails"]["mutates_stock"] is False
    assert view_model["guardrails"]["creates_purchase_order"] is False
    assert view_model["guardrails"]["approves_purchase_order"] is False
    assert view_model["actions"]["create_purchase_order_visible"] is False
    assert view_model["actions"]["approve_purchase_order_visible"] is False
    assert view_model["actions"]["stock_adjustment_visible"] is False
    assert view_model["rendering_rules"]["show_raw_model_internals"] is False
    assert view_model["rendering_rules"]["show_raw_movement_rows"] is False
    assert view_model["rendering_rules"]["duplicate_stock_history"] is False
    assert view_model["rendering_rules"]["duplicate_reorder_review"] is False
    assert view_model["rendering_rules"]["block_item_details_on_forecast_failure"] is False


def test_phase2e_available_view_model_example_matches_builder_output_shape():
    panel = _load_json("item_details_forecast_response_available.json")
    example = _load_json("item_details_view_model_available.json")

    built = build_item_details_forecast_view_model(panel)

    assert example["component"] == built["component"]
    assert example["status"] == built["status"]
    assert example["status_chip"] == built["status_chip"]
    assert example["snapshot"] == built["snapshot"]
    assert [field["key"] for field in example["fields"]] == [field["key"] for field in built["fields"]]
    assert example["fields"][0]["label"] == "Forecast demand next 30 days"
    assert example["fields"][-1]["key"] == "short_explanation"
    _assert_view_model_guardrails(example)


def test_phase2e_low_confidence_view_model_example_matches_builder_output_shape():
    panel = _load_json("item_details_forecast_response_low_confidence.json")
    example = _load_json("item_details_view_model_low_confidence.json")

    built = build_item_details_forecast_view_model(panel)

    assert example["component"] == built["component"]
    assert example["status"] == "low_confidence"
    assert example["status_chip"] == {"label": "Low confidence", "tone": "warning"}
    assert example["status_chip"] == built["status_chip"]
    assert any("Verify movement history" in warning for warning in example["warnings"])
    assert [field["key"] for field in example["fields"]] == [field["key"] for field in built["fields"]]
    _assert_view_model_guardrails(example)


def test_phase2e_unavailable_view_model_is_generated_from_unavailable_panel():
    panel = _load_json("item_details_forecast_response_unavailable.json")

    built = build_item_details_forecast_view_model(panel)

    assert built["status"] == "unavailable"
    assert built["title"] == "Forecast unavailable"
    assert built["fields"] == []
    assert built["snapshot"]["available"] is False
    assert built["actions"]["view_snapshot_visible"] is False
    assert built["fallback"]["item_details_usable"] is True
    assert built["fallback"]["stock_history_usable"] is True
    _assert_view_model_guardrails(built)
