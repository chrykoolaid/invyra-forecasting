# Program D2 — Error-Path Request Traceability

## Scope

Program D2 certifies that the request identifier foundation delivered in D1 remains available when API requests fail.

The certification covers:

- client-supplied request IDs on `404 Not Found` responses
- generated request IDs on error responses when clients omit the header
- client-supplied request IDs on FastAPI validation errors
- coexistence of request and tenant response headers on failures
- request-context isolation across sequential failed requests
- preservation of existing FastAPI error bodies

## Implementation Boundary

Program D2 introduces no new runtime middleware, exception handler, response envelope, persistence, audit storage, or distributed tracing backend.

The existing D1 middleware already applies the response header before the response leaves the ASGI boundary. D2 adds focused regression evidence so future changes cannot silently remove traceability from error paths.

## Preserved Boundaries

- Forecasting remains advisory-only and read-only.
- Inventory remains the operational source of truth.
- No inventory mutation or stock movement creation is introduced.
- No purchase-order creation or approval is introduced.
- No authentication, authorization, tenant provisioning, billing, cloud dependency, or distributed trace storage is introduced.
- Existing success and error payload contracts remain unchanged.
