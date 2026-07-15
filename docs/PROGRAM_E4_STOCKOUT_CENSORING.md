# Program E4 — Stockout Censoring Classification

Program E4 adds a read-only classification layer for actual-outcome evidence affected by stockouts.

It distinguishes:

- `uncensored`
- `partially_stockout_censored`
- `fully_stockout_censored`
- `insufficient_evidence`

The classifier consumes explicit stockout coverage and evidence references supplied by an external source of truth. It preserves the E3 observed quantity unchanged and records whether the evidence is eligible for later model-ranking use.

## Boundaries

- No lost-sales estimation.
- No missing-demand reconstruction.
- No observed-quantity adjustment.
- No automatic operational-data ingestion.
- No evaluation-formula or model-ranking behavior change.
- No inventory, stock movement, sales, transfer, wastage, markdown, or purchase-order mutation.
- Inventory remains the operational source of truth.
