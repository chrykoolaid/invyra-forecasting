# Program D6 — Explainability Constructor Compatibility

## Scope

Program D6 preserves the positional constructor contract of `HistoricalExplainabilityRecord` after D5 introduced optional request-correlation metadata.

The `metadata` field is placed after all pre-existing dataclass fields so callers using the established positional order continue to map `archived_at_utc`, advisory/read-only flags, and the Inventory source-of-truth flag correctly.

Focused regression tests certify legacy positional construction, keyword metadata support, and serialized request metadata.

## Preserved Boundaries

Program D6 does not change forecast calculations, model ranking, confidence, explanation content, evidence references, persistence format, API routes, tenant isolation, inventory state, stock movements, or purchase-order behavior.

Forecasting remains advisory-only and read-only. Inventory remains the operational source of truth.
