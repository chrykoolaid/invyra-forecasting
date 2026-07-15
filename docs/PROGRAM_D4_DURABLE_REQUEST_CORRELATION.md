# Program D4 — Durable Request Correlation

## Scope

Program D4 carries the active request identifier into immutable forecast-history metadata when a history record is created through `ForecastHistoryService`.

This closes the smallest remaining request-correlation gap after D1–D3: completed forecast history can now be traced back to the API request that produced it, and the identifier survives the existing local file persistence round trip.

## Compatibility

- History records created outside an HTTP request remain unchanged.
- Existing metadata is preserved.
- An explicitly supplied `metadata.request_id` is not overwritten.
- Existing history dataclasses, serialized shapes, API routes, and response envelopes remain compatible.
- Revisions capture the request identifier active when each new immutable version is created.

## Preserved Boundaries

Program D4 introduces no new API endpoint, mutation capability, authentication, authorization, tenant provisioning, billing, cloud dependency, or distributed tracing backend.

Forecasting remains advisory-only and read-only. Inventory remains the operational source of truth. No stock movement or purchase-order action is introduced, and forecast calculations, model ranking, confidence, explainability, evidence, snapshots, and tenant isolation remain unchanged.
