# Program D5 — Explainability Request Correlation

## Scope

Program D5 carries request identity into immutable historical explainability archives.

When `HistoricalExplainabilityArchiveService` runs inside an active request context, it adds the normalized request ID to archive metadata. Explicitly supplied `metadata.request_id` values remain authoritative, and archive creation outside request context remains backward compatible.

The optional metadata field is persisted by the existing file-backed archive format and defaults to an empty mapping when older records are decoded.

## Preserved Boundaries

Program D5 does not change forecast calculations, model ranking, confidence, explanation content, evidence references, history identity, API routes, tenant isolation, inventory state, stock movements, or purchase-order behavior.

Forecasting remains advisory-only and read-only. Inventory remains the operational source of truth. No authentication, authorization, cloud dependency, audit backend, or distributed tracing service is introduced.
