# Integration Contracts — Phase 1H

Phase 1H locks the first stable integration contracts for the main Invyra consumers of the forecasting engine.

The goal is to stop modules from guessing payloads, response fields, or governance behavior.

## Covered Modules

- Inventory
- ScanOps
- Reorder Review
- Dashboard
- Reports

## Contract Rules

1. Every module must preserve `environment` separation.
2. Forecasting is advisory only.
3. Inventory ledger remains the source of truth.
4. Forecast outputs must not mutate stock.
5. Reorder recommendations must not create or approve purchase orders automatically.
6. Low-confidence outputs must remain visible.
7. Fallback states must keep existing workflows usable.

## Inventory

Uses `POST /forecasts/item` for Item Details intelligence and `GET /snapshots/{snapshot_id}` for evidence readback.

Inventory must receive forecast quantity, days of cover, stockout risk, overstock risk, confidence, and explanation.

## ScanOps

Uses `POST /risk/stockout` for Gap Scan and Floor Scan risk interpretation.

ScanOps must not auto-adjust stock from forecasting output.

## Reorder Review

Uses `POST /recommendations/reorder` for suggested reorder quantity, urgency, risk, confidence, and explanation.

Reorder Review owns approval. Forecasting does not create purchase orders.

## Dashboard

Uses `POST /forecasts/batch` for batch risk summaries.

Dashboard must keep existing Priority Inventory Issues fallback if forecasting is unavailable.

## Reports

Uses `GET /reports/summary` for persisted forecast evidence summaries.

Reports must treat exports as operational evidence, not the inventory ledger.

## Code Registry

The machine-readable contract registry lives in:

```text
src/invyra_forecasting/integrations/registry.py
```

The registry can be imported by future modules, tests, or documentation generators.
