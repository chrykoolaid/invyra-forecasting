# Program E1 — Forecast Evaluation Linkage Foundation

## Scope

Program E1 adds an immutable identity link between an existing forecast-history record and an existing persisted forecast-evaluation record.

The linkage preserves and verifies:

- evaluation ID
- history ID
- forecast ID
- snapshot ID when available
- item and location identity
- model name and version
- forecast horizon
- history version

The service rejects mismatched forecast, item, location, model, version, and conflicting snapshot identities. Each persisted evaluation may be linked only once within the active tenant namespace.

## Architecture

The linkage layer references established records rather than copying forecast or evaluation payloads. Existing history and evaluation contracts remain unchanged.

The in-memory linkage repository is append-only and scoped through the existing tenant namespace context. Identical link IDs may exist in separate tenant namespaces without cross-tenant visibility.

## Preserved Boundaries

Program E1 does not change forecast calculations, evaluation formulas, confidence, calibration, model ranking, history records, evaluation records, snapshots, explainability, evidence generation, API routes, or persistence formats.

Forecasting remains advisory-only and read-only. Inventory remains the operational source of truth. No inventory mutation, stock movement, purchase-order creation, or purchase-order approval is introduced.

## Deferred

Program E1 does not introduce evaluation-window governance, actual-outcome ingestion, stockout-censoring classification, durable linkage persistence, public linkage APIs, or ranking-evidence eligibility rules. Those require separately scoped Program E increments.
