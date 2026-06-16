# Phase 2B — Item Details Forecast Service Boundary

Status: implemented foundation

## Objective

Phase 2B adds a stable, read-only service boundary for the future Inventory Item Details forecast intelligence panel.

This phase still does not modify Inventory UI. It prepares the response contract that Item Details can consume later without exposing model internals or breaking the existing item drill-down when forecasting is unavailable.

## Added Boundary

Package:

```text
src/invyra_forecasting/integrations/inventory/item_details.py
```

Primary entry point:

```python
ItemDetailsForecastBoundary
```

The boundary accepts Inventory adapter mapping input or raw Inventory-style mappings and returns one stable panel contract.

## Panel States

### `available`

Returned when the mapped Inventory data successfully produces a forecast and confidence is not low.

### `low_confidence`

Returned when the forecast succeeds but confidence rating is `Low`.

The forecast remains visible. The panel includes this warning:

```text
Low confidence forecast. Verify movement history, stock accuracy, and supplier lead time before acting.
```

### `unavailable`

Returned when mapping, validation, snapshot readback, or engine execution fails.

Item Details must remain usable. Stock History must remain usable. The panel includes a clear unavailable message instead of blocking the user.

## Clean Item Details Display Fields

The boundary intentionally exposes only daily-operator-safe fields:

- Forecast demand next 30 days
- Average daily demand
- Days of cover
- Stockout risk
- Overstock risk
- Suggested reorder quantity
- Confidence rating
- Confidence score
- Short explanation
- Last snapshot ID
- Generated time

It does not expose raw model internals or movement rows in the display contract.

## Evidence Readback

The boundary supports snapshot readback through:

```python
ItemDetailsForecastBoundary.read_snapshot_evidence(snapshot_id)
```

If evidence is missing, it returns an unavailable evidence state without breaking Item Details.

## Governance Flags

Every panel response includes advisory flags:

```json
{
  "advisory_only": true,
  "inventory_ledger_source_of_truth": true,
  "mutates_stock": false,
  "creates_purchase_order": false,
  "approves_purchase_order": false
}
```

These flags are deliberately repeated at the boundary level to make it hard for future UI or integration code to treat forecasting as stock truth or purchasing authority.

## Fallback Contract

Every response includes:

```json
{
  "item_details_usable": true,
  "stock_history_usable": true,
  "manual_review_available": true
}
```

This preserves the Phase 2 requirement that forecasting failure must not break Inventory Item Details.

## Tests

Added tests:

```text
tests/test_item_details_forecast_boundary.py
```

Coverage includes:

- Available forecast panel response.
- Snapshot persistence and readback.
- Low-confidence forecast remains visible.
- Forecast unavailable state when mapping fails.
- Missing snapshot evidence fallback.
- Engine failure fallback.
- Advisory-only, no-stock-mutation, and no-PO-creation flags.

## Phase 2B Exit Status

Phase 2B establishes the service response contract required before any UI work begins.

Next recommended phase:

```text
Phase 2C — API endpoint wrapper for Item Details forecast panel
```

Phase 2C should expose this boundary through a focused internal endpoint while preserving the same states and fallback contract.
