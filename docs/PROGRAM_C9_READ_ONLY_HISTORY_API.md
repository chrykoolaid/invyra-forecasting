# Program C9 — Read-Only History API Router

Program C9 introduces a production-envelope-compatible FastAPI router for durable forecast history.

Supported read operations:

- list and filter historical records
- retrieve one history record
- retrieve all versions for a forecast
- retrieve immutable lineage for a history version

The router reads from the C8 durable provider using `INVYRA_FORECAST_HISTORY_DIR` and `INVYRA_FORECAST_EXPLAINABILITY_DIR`. Tenant isolation is inherited from the existing request-scoped namespace context.

This phase intentionally does not register the router in the root API application. Root-app registration is isolated as the next small integration increment after router CI passes.

No creation, update, delete, inventory mutation, stock movement, purchase-order action, authentication, or authorization endpoint is introduced. Forecasting remains advisory-only and read-only. Inventory remains the operational source of truth.
