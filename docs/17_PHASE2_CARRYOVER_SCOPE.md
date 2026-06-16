# Phase 2 Carry-Over Scope — Inventory Integration Hardening

## Objective

Connect the Phase 1 forecasting engine to the real Invyra Inventory system in a controlled, read-only, advisory-first way.

## Primary Target

Inventory Item Details forecast intelligence panel.

This should be the first real integration because Item Details is already the item-level drill-down and is the safest place to surface forecast context without cluttering daily workflows.

## Phase 2 Principles

- Make it smarter, not harder.
- Keep screens clean.
- Do not duplicate modules.
- Preserve existing inventory logic.
- Forecasting is advisory only.
- Inventory ledger remains source of truth.
- Low-confidence forecasts must remain visible.
- Do not auto-create purchase orders.
- Do not auto-adjust stock.

## Required Phase 2 Work

1. Map real Inventory item fields to `ForecastRequest.item`.
2. Map real location/branch/storage fields to `ForecastRequest.location`.
3. Map live stock-on-hand and reserved stock to `ForecastRequest.stock_position`.
4. Map stock movement ledger records to `ForecastRequest.movements`.
5. Map supplier lead time and minimum order quantity to `ForecastRequest.supplier_profile`.
6. Preserve LIVE / TRAINING / TEST environment separation.
7. Display forecast results in Item Details as read-only intelligence.
8. Add low-confidence and unavailable states.
9. Add snapshot ID evidence readback.
10. Add audit logging for manager override behavior where applicable.

## Item Details UI Contract

Recommended fields to show:

- Forecast demand next 30 days
- Average daily demand
- Days of cover
- Stockout risk
- Overstock risk
- Suggested reorder quantity
- Confidence rating
- Short explanation
- Last snapshot ID / generated time

Do not show excessive model internals in the daily staff view.

## Fallback States

If forecasting is unavailable:

- Item Details must still load.
- Stock history and existing item details must remain usable.
- Show a simple forecast unavailable message.

If confidence is low:

- Show the forecast.
- Show a low-confidence warning.
- Recommend verifying movement history, stock accuracy, and supplier lead time.

## Out of Scope for Phase 2

- Advanced ML
- Auto-purchasing
- Supplier reliability scoring as final production signal
- CRM forecasting
- POS forecasting UI
- Full MLOps
- Full production deployment hardening

## Phase 2 Exit Criteria

- Inventory can request a forecast for a real item/location.
- Item Details can display forecast, risk, confidence, and explanation.
- Environment separation is preserved.
- No stock mutation occurs from forecast output.
- Tests cover real mapping adapters or fixtures.
- CI passes.
