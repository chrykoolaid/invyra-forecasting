# Phase 9C — Read-Only Client Contract Examples

## Status

Phase 9C provides adapter-level contract examples for downstream clients consuming the Phase 9A Forecast Decision Review API surface.

This phase is documentation-only. It does not add runtime behavior.

## Scope

Phase 9C documents how future clients can consume the existing read-only endpoints:

- Invyra Desktop Inventory
- Invyra Companion
- Base44 Inventory prototype
- future dashboard or reporting clients

The examples below describe projection consumption only.

## Endpoint Surface

### Decision Review Dashboard

```http
GET /forecast/decision-review/dashboard
```

Expected use:

- render decision review queue counts
- render queue item summaries
- display advisory forecast review state
- support manager visibility before any separate Inventory-side action

Client rule:

> Treat the response as read-only advisory projection data.

### Decision Review Export Bundle

```http
GET /forecast/decision-review/export
GET /forecast/decision-review/export?export_format=dict
```

Expected use:

- preview export-ready decision review payloads
- inspect export manifest metadata
- inspect validation status
- prepare future UI download/approval flows without writing files from the engine

Client rule:

> Treat the response as an export projection only. The forecasting engine does not write files or transmit export data.

## Dashboard Response Shape

A client should expect a response containing:

```json
{
  "response_version": "8H.1",
  "dashboard": {
    "summary": {
      "total_count": 0,
      "status_counts": {},
      "priority_counts": {},
      "advisory_only": true,
      "read_only": true,
      "inventory_source_of_truth_preserved": true
    },
    "snapshot": {
      "total_count": 0,
      "items": [],
      "advisory_only": true,
      "read_only": true,
      "inventory_source_of_truth_preserved": true
    },
    "advisory_only": true,
    "read_only": true,
    "inventory_source_of_truth_preserved": true
  },
  "advisory_only": true,
  "read_only": true,
  "inventory_source_of_truth_preserved": true
}
```

Clients should tolerate additional fields in future versions and should not assume response objects are exhaustive.

## Export Bundle Response Shape

A client should expect a response containing:

```json
{
  "bundle_version": "8L.1",
  "ready_for_delivery": true,
  "export": {
    "export_format": "json",
    "export_version": "8I.1",
    "response": {},
    "advisory_only": true,
    "read_only": true,
    "inventory_source_of_truth_preserved": true
  },
  "manifest": {
    "record_count": 0,
    "advisory_only": true,
    "read_only": true,
    "inventory_source_of_truth_preserved": true
  },
  "validation": {
    "valid": true,
    "warnings": [],
    "advisory_only": true,
    "read_only": true,
    "inventory_source_of_truth_preserved": true
  },
  "advisory_only": true,
  "read_only": true,
  "inventory_source_of_truth_preserved": true
}
```

Clients should treat `ready_for_delivery` as a projection readiness flag only. It is not approval, transmission, or operational execution.

## Error Handling Contract

Unsupported export formats return an HTTP validation response.

Example:

```http
GET /forecast/decision-review/export?export_format=csv
```

Expected response:

```json
{
  "detail": "Unsupported decision review export format"
}
```

Client rule:

> Do not retry unsupported export formats as operational writes. Surface the validation issue to the user or fall back to supported projection formats.

Currently supported projection formats:

- `json`
- `dict`

## Client-Side Adapter Pattern

Recommended downstream adapter behavior:

1. Fetch dashboard projection.
2. Verify `advisory_only`, `read_only`, and `inventory_source_of_truth_preserved` are true.
3. Render the projection without modifying Inventory state.
4. Route any operational action to Inventory-owned workflows only.

Pseudo-code:

```python
def load_forecast_review_dashboard(http_client):
    payload = http_client.get("/forecast/decision-review/dashboard").json()
    assert payload["advisory_only"] is True
    assert payload["read_only"] is True
    assert payload["inventory_source_of_truth_preserved"] is True
    return payload["dashboard"]
```

## Forbidden Client Behavior

Clients consuming these endpoints must not use the response to directly:

- decrement stock
- increment stock
- create stock movements
- create purchase orders
- approve purchase orders
- override ledger values
- mark forecasts as operational truth
- write export files from the forecasting engine process
- transmit export data from the forecasting engine process

## Ownership Boundary

Forecasting owns:

- advisory projections
- evidence-backed review packets
- queue/dashboard/export response shapes
- read-only API exposure

Inventory owns:

- stock ledger
- item master
- stock movements
- receiving
- purchasing
- purchase order lifecycle
- operational approvals
- audit authority for inventory mutation

## Phase 9C Lock

Phase 9C is locked as client contract documentation only.

No runtime behavior, mutation behavior, or new forecasting logic is introduced.

## Next Recommended Phase

Phase 9D may add read-only API integration tests or a stability marker for downstream adapter compatibility.

Phase 9D should remain read-only unless a separate approved scope defines otherwise.
