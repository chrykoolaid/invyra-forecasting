# Phase 2D — API Examples and Integration Fixture Hardening

Status: implemented foundation

## Objective

Phase 2D adds practical developer-facing examples for the Inventory Item Details forecast API before any Inventory UI wiring begins.

This phase keeps forecasting integration advisory, read-only, and UI-safe. It gives Inventory developers enough examples to wire the Item Details panel later without exposing engine internals or guessing response states.

## Added Example Directory

```text
examples/api/inventory_item_details/
```

## Request Examples

```text
item_details_forecast_request.json
item_details_forecast_request_low_confidence.json
item_details_forecast_request_unavailable.json
```

These examples cover the three supported panel states:

- `available`
- `low_confidence`
- `unavailable`

## Response Examples

```text
item_details_forecast_response_available.json
item_details_forecast_response_low_confidence.json
item_details_forecast_response_unavailable.json
item_details_snapshot_response_available.json
item_details_snapshot_response_unavailable.json
```

These examples show the expected panel contract and snapshot evidence contract for Inventory developers.

## Developer README

```text
examples/api/inventory_item_details/README.md
```

The README includes:

- local API startup command
- `POST /inventory/item-details/forecast` curl example
- low-confidence curl example
- unavailable curl example
- snapshot evidence readback example
- UI display rules
- advisory governance rules
- fallback handling rules

## Fixture Hardening Tests

Added tests:

```text
tests/test_phase2d_inventory_api_examples.py
```

Coverage includes:

- Request examples validate against `ItemDetailsForecastPanelRequest`.
- Request examples produce the expected API states.
- Response examples preserve the stable panel shape.
- Snapshot response examples preserve evidence and missing-evidence shape.
- Advisory flags are present and fixed.
- Fallback flags are present and fixed.
- README documents endpoint usage and governance requirements.

## Governance Preserved

Phase 2D does not:

- modify Inventory UI
- mutate stock
- create purchase orders
- approve purchase orders
- change ledger truth
- hide low-confidence forecasts
- block Item Details when forecasting is unavailable

Every panel response continues to preserve:

```json
{
  "advisory_only": true,
  "inventory_ledger_source_of_truth": true,
  "mutates_stock": false,
  "creates_purchase_order": false,
  "approves_purchase_order": false
}
```

Every panel response also preserves:

```json
{
  "item_details_usable": true,
  "stock_history_usable": true,
  "manual_review_available": true
}
```

## Phase 2D Exit Status

Phase 2D establishes developer-facing API examples and example validation before UI wiring.

Next recommended phase:

```text
Phase 2E — Item Details UI integration scope and view-model contract
```

Phase 2E should define the UI view-model and display rules first. It should still avoid broad Inventory UI rewrites and should not duplicate Stock History, Reorder Review, or Dashboard logic.
