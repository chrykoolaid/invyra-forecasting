# Phase 9B — API Exposure Lock Marker

## Status

Phase 9B is a documentation-only lock marker following the successful Phase 9A read-only endpoint wiring.

Phase 9A exposed the existing Phase 8 Forecast Decision Review projection chain through read-only API endpoints.

## Locked Phase 9A Surface

The Phase 9A API surface is limited to:

- `GET /forecast/decision-review/dashboard`
- `GET /forecast/decision-review/export`

These endpoints expose existing Phase 8 projections only:

- decision review dashboard response projections
- decision review export projections
- export manifests
- export validation results
- export bundles

## Governance Lock

The exposed API surface remains:

- advisory-only
- read-only
- evidence-backed
- audit-friendly
- safe for future UI and desktop integration

The exposed API surface does not:

- mutate inventory
- create stock movements
- create purchase orders
- approve purchase orders
- write export files
- transmit export data
- override ledger truth
- introduce new forecasting logic

Inventory remains the source of truth.

## Integration Boundary

Phase 9B confirms that future UI/Desktop/API integration should consume these endpoints as projection readers only.

Any future write-capable workflow must remain outside this API surface and must be governed by Inventory as the system of record.

## Next Recommended Phase

Phase 9C should focus on API integration documentation or adapter-level contract examples for downstream clients.

Phase 9C should not add mutation behavior or new forecasting logic unless separately scoped and approved.
