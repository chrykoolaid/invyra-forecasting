# Program E5 — Evaluation Persistence Integration

Program E5 adds a separate append-only persistence layer for the evidence contracts delivered by E1–E4.

It persists immutable snapshots of:

- forecast-to-evaluation linkage;
- evaluation-window assessment;
- normalized actual outcome evidence;
- stockout-censoring assessment.

The repository supports partial evidence followed by one final evidence record, tenant-isolated lookup, JSONL durability, and reconstruction after restart. A second final record for the same evaluation is rejected within the same tenant namespace.

Final evidence requires both final-window eligibility and complete uncensored outcome evidence. Partial evidence may be retained while a horizon remains open or evidence remains incomplete.

## Boundaries

- Existing forecast-history and evaluation records remain unchanged.
- Existing evaluation formulas and model-ranking behaviour remain unchanged.
- No automatic operational-data ingestion.
- No lost-sales estimation or demand reconstruction.
- No inventory, stock movement, sales, transfer, wastage, markdown, or purchase-order mutation.
- Forecasting remains advisory-only and read-only.
- Inventory remains the operational source of truth.
