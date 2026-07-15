# Program D3 — Request ID Input Hardening

## Scope

Program D3 hardens client-supplied `X-Request-Id` values before they are returned in response headers or stable API metadata.

Accepted identifiers:

- are trimmed
- contain visible ASCII characters only
- are no longer than 128 characters

Blank, oversized, control-character, or non-ASCII values are replaced with generated UUID request identifiers.

## Compatibility

Valid existing request identifiers continue to pass through unchanged. Generated identifiers remain request-scoped and continue to appear in every HTTP response and stable `/v1` metadata.

Tenant headers and tenant-isolation behavior remain unchanged.

## Preserved Boundaries

Program D3 does not introduce authentication, authorization, persistence, distributed tracing storage, inventory mutation, stock movements, or purchase-order creation or approval.

Forecast calculations, model ranking, confidence, explainability, evidence, snapshots, and history remain unchanged. Inventory remains the operational source of truth, and forecasting remains advisory-only.
