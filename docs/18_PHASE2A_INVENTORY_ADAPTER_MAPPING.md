# Phase 2A — Inventory Adapter Contract and Mapping Layer

Status: implemented foundation

## Objective

Phase 2A adds the first read-only Inventory integration foundation for the forecasting engine.

This phase does not modify Inventory UI, stock records, purchase orders, or ledger data. It only maps Inventory-owned records into the existing `ForecastRequest` contract so the engine can later be called from the Inventory Item Details forecast intelligence panel.

## Governance Locks Preserved

- Forecasting remains advisory only.
- Inventory ledger remains the source of truth.
- Forecasting does not mutate stock.
- Forecasting does not create or approve purchase orders.
- LIVE / TRAINING / TEST separation is enforced before a request is produced.
- Low-confidence and unavailable UI handling remain Phase 2B+ work.
- Item Details remains the safest first UI target, but no UI work is included in Phase 2A.

## Added Mapping Layer

Package:

```text
src/invyra_forecasting/integrations/inventory/
```

Primary entry points:

- `InventoryForecastMapper`
- `InventoryForecastMappingInput`
- `map_inventory_to_forecast_request`

Source record contracts:

- `InventoryItemRecord`
- `InventoryLocationRecord`
- `InventoryStockPositionRecord`
- `InventoryMovementLedgerRecord`
- `InventorySupplierProfileRecord`

Error contract:

- `InventoryAdapterMappingError`

## Field Mapping Summary

| Inventory source concept | Forecast request target |
|---|---|
| Item ID / inventory item ID | `ForecastRequest.item.item_id` |
| SKU / barcode / primary barcode | `ForecastRequest.item.sku` |
| Item name / product name / description | `ForecastRequest.item.name` |
| Category / department | `ForecastRequest.item.category` |
| Unit / UOM | `ForecastRequest.item.unit_of_measure` |
| Minimum order quantity / MOQ / case pack | `ForecastRequest.item.minimum_order_quantity` |
| Branch / store / storage area ID | `ForecastRequest.location.location_id` |
| Branch / store / storage area name | `ForecastRequest.location.name` |
| Stock on hand / SOH / quantity on hand | `ForecastRequest.stock_position.on_hand` |
| Reserved / committed / allocated stock | `ForecastRequest.stock_position.reserved` |
| Ledger movement ID | `ForecastRequest.movements[].movement_id` |
| Ledger movement date / created timestamp | `ForecastRequest.movements[].movement_date` |
| Ledger movement type / reason / source | `ForecastRequest.movements[].movement_type` |
| Ledger quantity / delta quantity | `ForecastRequest.movements[].quantity` |
| Supplier ID / primary supplier ID | `ForecastRequest.supplier_profile.supplier_id` |
| Supplier lead time | `ForecastRequest.supplier_profile.lead_time_days` |
| Lead time variability | `ForecastRequest.supplier_profile.lead_time_variability_days` |

## Movement Mapping Notes

Inventory ledger quantities may be signed in operational systems. The forecasting request contract expects non-negative movement quantities because movement direction is represented by `MovementType`.

Phase 2A therefore maps signed ledger quantities to absolute movement magnitude and preserves direction through the mapped movement type.

Known aliases include:

- `POS_AUTO_DEDUCTION` -> `POS_SALE`
- `RECEIVING` / `DELIVERY_RECEIPT` -> `RECEIPT`
- `WASTE` -> `WASTAGE`
- `MARKDOWN` -> `MARKDOWN_SALE`
- `STOCKTAKE` -> `STOCKTAKE_VARIANCE`
- `GAP_SCAN` -> `GAP_SCAN_CAPTURE`
- `FLOOR_SCAN` -> `FLOOR_SCAN_CAPTURE`

Unsupported movement types fail closed with `InventoryAdapterMappingError`.

## Phase 2A Tests

Added tests:

```text
tests/test_inventory_adapter_mapping.py
```

Coverage includes:

- Mapping a realistic Item Details source fixture to `ForecastRequest`.
- Validating the mapped request against existing forecast input validation.
- Preserving environment separation.
- Rejecting cross-environment stock position data.
- Rejecting cross-environment movement ledger data.
- Rejecting movements for a different item.
- Rejecting unsupported movement types.

Fixture:

```text
integrations/inventory/fixtures/phase2a_item_details_source.json
```

## Phase 2A Exit Status

Phase 2A establishes the safe mapping foundation required before Inventory UI work begins.

Next recommended phase:

```text
Phase 2B — Item Details forecast service boundary and unavailable-state contract
```

Phase 2B should connect the mapped request to the forecast service boundary while still avoiding direct UI changes until the service response and fallback states are proven.
