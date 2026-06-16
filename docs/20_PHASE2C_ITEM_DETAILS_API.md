# Phase 2C — Item Details Forecast API Wrapper

Status: implemented foundation

## Objective

Phase 2C exposes the Phase 2B Item Details forecast boundary through focused internal API endpoints.

This phase still does not modify Inventory UI. It creates the API wrapper that Inventory can call later from the Item Details forecast intelligence panel.

## New API Contract

```text
src/invyra_forecasting/api/inventory_contracts.py
```

Primary request model:

```python
ItemDetailsForecastPanelRequest
```

The request accepts Inventory-owned source mappings rather than requiring Inventory UI code to know the lower-level forecasting engine payload.

Required source sections:

- `item`
- `location`
- `stock_position`
- `movements`
- `supplier_profile`
- `environment`

Optional controls:

- `actor`
- `persist_snapshot`
- `forecast_horizon_days`
- `demand_lookback_days`
- `target_cover_days`
- `safety_stock_days`
- `anchor_date`

## New Endpoints

### Build Item Details Forecast Panel

```http
POST /inventory/item-details/forecast
```

Returns the same stable panel contract from Phase 2B:

- `available`
- `low_confidence`
- `unavailable`

The endpoint must not raise a hard API error for normal forecast unavailability. Mapping failures, validation failures, and engine failures are converted into the safe `unavailable` panel state so Item Details can still load.

### Read Item Details Forecast Snapshot Evidence

```http
GET /inventory/item-details/forecast/snapshots/{snapshot_id}
```

Returns persisted snapshot evidence when available.

If the snapshot is missing, the endpoint returns a safe `unavailable` evidence state instead of breaking the caller.

## Governance Preserved

Every panel response still includes advisory flags:

```json
{
  "advisory_only": true,
  "inventory_ledger_source_of_truth": true,
  "mutates_stock": false,
  "creates_purchase_order": false,
  "approves_purchase_order": false
}
```

The API wrapper does not:

- mutate stock
- create purchase orders
- approve purchase orders
- replace Inventory ledger truth
- hide low-confidence forecasts
- block Item Details when forecasting is unavailable

## Fallback Preserved

The API wrapper preserves the Phase 2B fallback contract:

```json
{
  "item_details_usable": true,
  "stock_history_usable": true,
  "manual_review_available": true
}
```

## Tests

Added tests:

```text
tests/test_inventory_item_details_api.py
```

Coverage includes:

- Available panel response through the API wrapper.
- Snapshot persistence and evidence readback through the API wrapper.
- Low-confidence state through the API wrapper.
- Unavailable state through the API wrapper.
- Missing snapshot evidence fallback.
- Optional snapshot persistence disabled.
- Advisory-only / no-stock-mutation / no-PO flags.

## Phase 2C Exit Status

Phase 2C establishes the internal API wrapper needed before Inventory UI wiring begins.

Next recommended phase:

```text
Phase 2D — API examples and integration fixture hardening
```

Phase 2D should add curl examples, JSON examples, and endpoint usage docs for Inventory developers before any UI work is attempted.
