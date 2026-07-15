# Program E2 — Evaluation Window Governance

Program E2 adds a read-only eligibility classifier for linked forecast history and evaluation evidence.

It distinguishes:

- `not_yet_evaluable`
- `partially_evaluable`
- `fully_evaluable`
- `insufficient_actual_data`
- `evaluated`

The classifier uses the immutable history creation timestamp, the E1 forecast horizon, an explicit assessment timestamp, and caller-supplied actual-data completeness. It does not ingest operational data, create evaluation records, change evaluation formulas, or alter model ranking.

## Guardrails

- Advisory-only and read-only.
- Inventory remains the operational source of truth.
- No inventory, stock movement, or purchase-order mutation.
- No automatic evaluation execution.
- No inferred or invented actual demand.
- No API or persistence-format change.
