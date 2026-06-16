# API Contracts — Phase 1B

The API layer is an internal integration wrapper around the Python-first forecasting engine.

It does not own forecasting logic. It validates payloads, converts them into typed engine bundles, calls `ForecastingService`, and returns primitive JSON-safe output.

## Routes

- `GET /health`
- `POST /forecasts/item`
- `POST /forecasts/batch`
- `POST /risk/stockout`
- `POST /recommendations/reorder`
- `POST /audit/override`

## Forecast Request Shape

```json
{
  "actor": "inventory-ui",
  "environment": "TRAINING",
  "forecast_horizon_days": 30,
  "demand_lookback_days": 30,
  "target_cover_days": 14,
  "safety_stock_days": 3,
  "anchor_date": "2026-06-16",
  "write_snapshot": false,
  "item": {
    "item_id": "ITEM-001",
    "sku": "SKU-COFFEE-250",
    "name": "Coffee Beans 250g",
    "category": "Grocery",
    "unit_of_measure": "unit",
    "minimum_order_quantity": 6
  },
  "location": {
    "location_id": "LOC-001",
    "name": "Training Store",
    "location_type": "STORE"
  },
  "stock_position": {
    "item_id": "ITEM-001",
    "location_id": "LOC-001",
    "on_hand": 18,
    "reserved": 0,
    "environment": "TRAINING"
  },
  "movements": [
    {
      "movement_id": "MOV-001",
      "item_id": "ITEM-001",
      "location_id": "LOC-001",
      "movement_date": "2026-06-16",
      "movement_type": "POS_SALE",
      "quantity": 3,
      "environment": "TRAINING"
    }
  ],
  "supplier_profile": {
    "supplier_id": "SUP-001",
    "item_id": "ITEM-001",
    "lead_time_days": 5,
    "lead_time_variability_days": 1,
    "minimum_order_quantity": 6
  }
}
```

## Governance Behaviour

- Environment mismatches return HTTP 400.
- Forecasting remains advisory.
- API endpoints do not mutate inventory stock.
- Reorder endpoints return recommendations only; they do not create purchase orders.
- Override audit endpoint creates an audit event only; it does not approve, reject, or change inventory records.
