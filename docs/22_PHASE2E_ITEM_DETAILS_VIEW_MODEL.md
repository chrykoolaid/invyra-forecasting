# Phase 2E — Item Details UI View-Model Contract

Status: implemented foundation

## Objective

Phase 2E defines the UI-facing view-model contract for the future Inventory Item Details forecast intelligence panel.

This phase does not wire or modify the real Inventory UI. It creates a framework-neutral contract that tells the UI exactly what to render later and what not to render.

## Added View-Model Builder

```text
src/invyra_forecasting/integrations/inventory/view_model.py
```

Primary entry points:

```python
ItemDetailsForecastViewModelBuilder
build_item_details_forecast_view_model(panel)
```

The builder converts the Phase 2B / Phase 2C panel response into a clean UI contract.

## Supported States

The UI view-model supports exactly three states:

```text
available
low_confidence
unavailable
```

Unknown states fail closed with `ItemDetailsForecastViewModelError`.

## Component Contract

The view-model uses this component name:

```text
InventoryItemDetailsForecastPanel
```

The intended UI location is inside Inventory Item Details as a compact intelligence panel.

## Display Field Order

The UI should render these fields only, in this order:

1. Forecast demand next 30 days
2. Average daily demand
3. Days of cover
4. Stockout risk
5. Overstock risk
6. Suggested reorder quantity
7. Confidence
8. Explanation

Do not show raw model internals, raw movement rows, debug data, or full snapshot internals in the daily staff panel.

## Chip Rules

### Status chip

| State | Label | Tone |
|---|---|---|
| `available` with High confidence | High | success |
| `available` with Medium confidence | Medium | warning |
| `available` with unknown confidence | Unknown | neutral |
| `low_confidence` | Low confidence | warning |
| `unavailable` | Unavailable | neutral |

### Risk chip

| Risk | Tone |
|---|---|
| High | danger |
| Medium | warning |
| Low | success |
| unknown | neutral |

## Low-Confidence Rule

Low-confidence forecasts must remain visible.

The view-model ensures this warning is present:

```text
Low confidence forecast. Verify movement history, stock accuracy, and supplier lead time before acting.
```

## Unavailable Rule

When forecasting is unavailable:

- render no forecast fields
- show `Forecast unavailable`
- keep Item Details usable
- keep Stock History usable
- allow manual review
- hide snapshot evidence link

Required message:

```text
Forecast unavailable. Item Details and stock history remain usable.
```

## Snapshot Evidence Rule

When a snapshot ID exists, the UI may show a simple link/button:

```text
View forecast evidence
```

When no snapshot ID exists, the UI must not show a broken evidence link.

## Action Visibility Rules

The view-model intentionally exposes safe action flags:

```json
{
  "refresh_forecast_visible": true,
  "view_snapshot_visible": true,
  "manual_review_visible": true,
  "create_purchase_order_visible": false,
  "approve_purchase_order_visible": false,
  "stock_adjustment_visible": false
}
```

The unavailable state sets `view_snapshot_visible` to `false`.

## Guardrails

Every view-model includes guardrails:

```json
{
  "advisory_only": true,
  "inventory_ledger_source_of_truth": true,
  "mutates_stock": false,
  "creates_purchase_order": false,
  "approves_purchase_order": false,
  "notice": "Forecasting is advisory. Inventory ledger remains the source of truth."
}
```

## Rendering Rules

Every view-model includes rendering rules:

```json
{
  "show_raw_model_internals": false,
  "show_raw_movement_rows": false,
  "duplicate_stock_history": false,
  "duplicate_reorder_review": false,
  "block_item_details_on_forecast_failure": false
}
```

These rules protect the Item Details screen from becoming cluttered or duplicating existing Inventory workflows.

## Examples

Added examples:

```text
examples/api/inventory_item_details/item_details_view_model_available.json
examples/api/inventory_item_details/item_details_view_model_low_confidence.json
```

The unavailable state is covered by executable tests and this document.

## Tests

Added tests:

```text
tests/test_item_details_forecast_view_model.py
tests/test_phase2e_inventory_view_model_examples.py
```

Coverage includes:

- available view-model shape
- low-confidence visible forecast and warning
- unavailable fallback view-model
- snapshot visibility behavior
- clean field order
- no raw movement rows
- no model internals
- no Stock History duplication
- no Reorder Review duplication
- no stock mutation actions
- no PO creation or approval actions
- unknown status fails closed
- example view-model alignment

## Phase 2E Exit Status

Phase 2E establishes the UI-facing contract required before real Inventory UI wiring begins.

Next recommended phase:

```text
Phase 2F — Item Details UI wiring plan and integration guard tests
```

Phase 2F should define the implementation plan for connecting this view-model to the actual Inventory Item Details panel, including guard tests that prove Stock History, Reorder Review, ledger truth, and fallback behavior remain intact.
