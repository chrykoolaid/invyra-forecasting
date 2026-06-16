# Phase 2F — Item Details UI Wiring Plan and Guard Tests

Status: implemented planning guard

## Objective

Phase 2F defines the real Inventory Item Details UI wiring plan and adds executable guard tests before actual UI wiring begins.

This phase does not modify the Inventory UI. It protects the next implementation phase by defining exactly where the forecast panel belongs, what it may consume, and what it must not change.

## Added Guard Module

```text
src/invyra_forecasting/integrations/inventory/ui_wiring_plan.py
```

Primary entry points:

```python
get_item_details_ui_wiring_plan()
validate_item_details_ui_wiring_plan(plan)
assert_valid_item_details_ui_wiring_plan(plan)
```

The wiring plan is an executable contract that future UI work can validate before implementation.

## Locked UI Placement

The forecast panel belongs inside:

```text
Inventory Item Details
```

Recommended placement:

```text
Item Details intelligence section
```

Recommended layout:

```text
compact_panel
```

The panel may be collapsible, but it must not block existing Item Details content.

## Required Data Sources

The UI wiring must use:

```text
POST /inventory/item-details/forecast
GET /inventory/item-details/forecast/snapshots/{snapshot_id}
build_item_details_forecast_view_model
```

Inventory UI should consume the view-model output, not raw engine internals.

## Required States

The wiring plan supports exactly:

```text
available
low_confidence
unavailable
```

### Available

Render the locked field order and show snapshot evidence when available.

### Low confidence

Render the forecast fields, keep the forecast visible, and show the low-confidence warning.

### Unavailable

Render no forecast fields, do not show a broken snapshot link, and keep Item Details plus Stock History usable.

## Locked Field Order

Visible forecast states must render only:

1. Forecast demand next 30 days
2. Average daily demand
3. Days of cover
4. Stockout risk
5. Overstock risk
6. Suggested reorder quantity
7. Confidence
8. Explanation

## Must Preserve

The UI wiring must preserve:

- Item Details usability
- Stock History usability
- Manual review availability
- Inventory ledger as source of truth
- LIVE / TRAINING / TEST environment separation
- Low-confidence forecast visibility
- Optional snapshot evidence behavior

## Must Not Do

The UI wiring must not:

- mutate stock
- create purchase orders
- approve purchase orders
- auto-reorder
- hide low-confidence forecasts
- block Item Details when forecasting fails
- duplicate Stock History
- duplicate Reorder Review
- show raw model internals
- show raw movement rows

## Forbidden Duplications

The forecast panel must not recreate or replace:

- Stock History
- Reorder Review
- Dashboard Priority Issues
- Movement Ledger
- Purchase Order Approval

## Guard Tests

Added tests:

```text
tests/test_item_details_ui_wiring_plan.py
```

Coverage includes:

- locked plan is valid
- required endpoints are fixed
- required view-model builder is fixed
- clean field order is locked
- existing Item Details remains usable
- Stock History remains usable
- low-confidence forecasts remain visible
- unavailable state does not block Item Details
- purchase order actions are blocked
- stock mutation actions are blocked
- duplicate module behavior is blocked
- wrong field order fails validation
- unsafe plan changes fail closed
- wiring plan returns a copy, not mutable global state

## Phase 2F Exit Status

Phase 2F establishes the guardrail layer required before actual UI wiring.

Next recommended phase:

```text
Phase 2G — Inventory Item Details UI wiring implementation
```

Phase 2G may begin actual UI wiring only if it uses the Phase 2F plan and preserves all guard tests.
