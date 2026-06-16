# Inventory Item Details Forecast API Examples

These examples are for the Phase 2 Inventory integration path.

The endpoint is designed for the Inventory Item Details forecast intelligence panel. It is advisory-only and must not be treated as stock truth or purchasing authority.

## Start the API locally

```bash
pip install -e ".[dev]"
uvicorn invyra_forecasting.api.app:app --reload
```

Default local base URL:

```text
http://127.0.0.1:8000
```

## Build the Item Details forecast panel

```bash
curl -X POST "http://127.0.0.1:8000/inventory/item-details/forecast" \
  -H "Content-Type: application/json" \
  --data @examples/api/inventory_item_details/item_details_forecast_request.json
```

Expected response state:

```text
available
```

## Low-confidence example

```bash
curl -X POST "http://127.0.0.1:8000/inventory/item-details/forecast" \
  -H "Content-Type: application/json" \
  --data @examples/api/inventory_item_details/item_details_forecast_request_low_confidence.json
```

Expected response state:

```text
low_confidence
```

The forecast remains visible. The UI should show the warning and prompt the user to verify movement history, stock accuracy, and supplier lead time before acting.

## Unavailable example

```bash
curl -X POST "http://127.0.0.1:8000/inventory/item-details/forecast" \
  -H "Content-Type: application/json" \
  --data @examples/api/inventory_item_details/item_details_forecast_request_unavailable.json
```

Expected response state:

```text
unavailable
```

The UI must keep Item Details and Stock History usable.

## Read snapshot evidence

Use the `snapshot_id` returned from the panel response:

```bash
curl "http://127.0.0.1:8000/inventory/item-details/forecast/snapshots/example-snapshot-id"
```

If the snapshot is missing, the endpoint returns a safe `unavailable` evidence state instead of breaking Item Details.

## Example files

| File | Purpose |
|---|---|
| `item_details_forecast_request.json` | Normal request expected to return `available` |
| `item_details_forecast_request_low_confidence.json` | Request expected to return `low_confidence` |
| `item_details_forecast_request_unavailable.json` | Request expected to return `unavailable` |
| `item_details_forecast_response_available.json` | Example `available` panel response |
| `item_details_forecast_response_low_confidence.json` | Example `low_confidence` panel response |
| `item_details_forecast_response_unavailable.json` | Example `unavailable` panel response |
| `item_details_snapshot_response_available.json` | Example snapshot evidence response |
| `item_details_snapshot_response_unavailable.json` | Example missing snapshot fallback |

## UI handling rules

Inventory Item Details should only show the clean `display_fields` values:

- Forecast demand next 30 days
- Average daily demand
- Days of cover
- Stockout risk
- Overstock risk
- Suggested reorder quantity
- Confidence rating
- Short explanation
- Last snapshot ID / generated time

Do not show raw model internals, raw movement rows, or debug information in the daily staff view.

## Governance rules

Every panel response includes advisory flags. Inventory UI and downstream modules must preserve them:

```json
{
  "advisory_only": true,
  "inventory_ledger_source_of_truth": true,
  "mutates_stock": false,
  "creates_purchase_order": false,
  "approves_purchase_order": false
}
```

Forecasting must not:

- mutate stock
- create purchase orders
- approve purchase orders
- replace Inventory ledger truth
- hide low-confidence forecasts
- block Item Details when forecasting is unavailable

## Fallback rule

When `status` is `unavailable`, show a simple forecast unavailable message and keep the rest of Item Details usable.

```text
Forecast unavailable. Item Details and stock history remain usable.
```
