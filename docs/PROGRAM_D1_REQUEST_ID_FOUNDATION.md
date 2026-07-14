# Program D1 — Request ID Foundation

## Scope

Program D1 adds request-scoped trace identifiers to the existing FastAPI boundary.

- Clients may supply `X-Request-Id`.
- Blank or missing identifiers are replaced with generated UUIDs.
- Every HTTP response returns `X-Request-Id`.
- Stable `/v1` production envelopes include `metadata.request_id`.
- Request identifiers remain isolated across requests through `ContextVar` state.
- `X-Request-Id` is included in the explicit CORS allow-list.

## Preserved Boundaries

Program D1 does not introduce authentication, authorization, tenant provisioning, billing, distributed tracing storage, inventory mutation, stock movements, or purchase-order creation or approval.

Forecast calculations, model ranking, confidence, explainability, evidence, snapshots, history, and tenant isolation remain unchanged.

Inventory remains the operational source of truth, and forecasting remains advisory-only.
