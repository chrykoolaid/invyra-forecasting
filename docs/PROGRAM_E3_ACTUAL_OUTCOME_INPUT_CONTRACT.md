# Program E3 — Actual Outcome Input Contract

Program E3 adds a normalized, read-only contract for actual outcome evidence used by forecast evaluation.

The contract records:

- forecast, item, and location identity;
- an explicit UTC measurement window;
- observed quantity supplied by an external source of truth;
- source and evidence references;
- actual-data completeness aligned with the E2 assessment;
- optional explanatory notes.

## Boundaries

- The forecasting engine does not ingest operational data automatically.
- It does not calculate or infer missing demand.
- It does not classify stockout censoring; that remains a later, separate scope.
- It does not modify inventory, stock movements, sales, transfers, wastage, markdowns, or purchase orders.
- Inventory remains the operational source of truth.
- No evaluation formula, model ranking, API, or persistence format is changed.
