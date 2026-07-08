# Phase 10A — Controlled Desktop Integration Planning

## Status

Phase 10A defines the controlled planning boundary for future Invyra Desktop consumption of the locked Phase 9 read-only Forecast Decision Review API.

This phase is documentation and readiness verification only.

It does not add runtime behavior, endpoint behavior, desktop code, or forecasting logic.

## Integration Goal

Invyra Desktop may consume Forecast Decision Review projections to support manager/operator visibility while preserving Inventory as the operational system of record.

The forecasting engine remains advisory-only and read-only.

## Approved Read-Only API Surface

Future desktop integration may consume only:

```http
GET /forecast/decision-review/dashboard
GET /forecast/decision-review/export
GET /forecast/decision-review/export?export_format=dict
```

Unsupported formats remain validation failures and must not be retried as operational actions.

## Desktop Consumption Use Cases

Approved desktop use cases:

- show forecast decision review dashboard counts
- show review queue item summaries
- preview export bundle readiness
- display validation warnings
- display evidence-backed advisory context
- support manager review preparation

Not approved in Phase 10A:

- creating stock movements
- creating purchase orders
- approving purchase orders
- changing ledger values
- writing export files from the forecasting engine
- transmitting export data from the forecasting engine
- treating forecast projections as operational truth

## Desktop Adapter Boundary

A future Desktop adapter should:

1. Use the Phase 9 reference client or equivalent read-only HTTP client.
2. Verify governance flags before rendering.
3. Ignore unknown optional fields.
4. Render dashboard/export projections as advisory information.
5. Route every operational action to Inventory-owned workflows.
6. Fail closed if governance flags are missing or false.

## Required Governance Flags

Desktop consumers must confirm:

```text
advisory_only == true
read_only == true
inventory_source_of_truth_preserved == true
```

If any guardrail fails, the Desktop UI should not display the payload as trusted guidance.

## UI Placement Recommendation

Recommended future placement in Invyra Desktop:

- Inventory Dashboard: read-only Forecast Review summary card
- Item Details: optional read-only forecast review context panel
- Reports: read-only export preview entry point
- Admin/Settings: read-only API connectivity status

No Phase 10A work implements these screens.

## Integration Sequence

Recommended future integration sequence:

1. Desktop adapter stub reads the dashboard endpoint.
2. Desktop adapter verifies governance flags.
3. Desktop UI renders read-only summary card.
4. Desktop adapter reads export bundle projection.
5. Desktop UI displays validation status only.
6. Operational actions remain routed to Inventory services.
7. Pilot validation confirms no mutation path exists from forecasting.

## Failure Handling

Desktop consumers should handle failures as non-blocking advisory unavailability.

Recommended behavior:

- API unavailable: show forecast review unavailable
- unsupported export format: show validation message
- missing governance flags: fail closed
- invalid response shape: fail closed
- timeout: show non-blocking advisory warning

Forecasting API failures must not block Inventory ledger workflows.

## Guardrails

Phase 10A preserves:

- advisory-only
- read-only
- no new forecasting logic
- no API behavior changes
- no desktop runtime implementation
- no inventory mutation
- no stock movement creation
- no purchase order creation
- no purchase order approval
- no export file writing
- no export data transmission
- Inventory remains source of truth

## Phase 10A Lock

Phase 10A is complete when:

- this desktop integration plan exists
- readiness tests confirm the planning boundary
- CI is green
- the Phase 10A PR is merged into `main`

Future desktop integration work must be separately scoped and must preserve the Phase 9 read-only API contract unless explicitly reopened by a governed phase.
