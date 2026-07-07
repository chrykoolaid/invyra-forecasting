# Phase 9F — Consumer Integration Handoff

## Status

This handoff package supports future read-only consumers of the Forecast Decision Review API.

It is documentation-only and introduces no runtime behavior.

## Intended Consumers

Approved downstream consumers may include:

- Invyra Desktop Inventory
- Invyra Companion
- Base44 Inventory prototype
- internal dashboard clients
- reporting clients

## Integration Goal

Consumers should render forecast decision review projections without treating them as operational truth.

The forecasting engine provides advisory decision-support data only.

Inventory remains the operational system of record.

## Available Read-Only Endpoints

### Dashboard Projection

```http
GET /forecast/decision-review/dashboard
```

Use for:

- review queue counts
- review queue item visibility
- dashboard summary cards
- manager/operator review preparation

Do not use for:

- stock mutation
- purchase order creation
- approval workflows
- ledger override

### Export Bundle Projection

```http
GET /forecast/decision-review/export
GET /forecast/decision-review/export?export_format=dict
```

Use for:

- export preview
- manifest inspection
- validation status display
- read-only report preparation

Do not use for:

- writing files from the forecasting engine
- transmitting data from the forecasting engine
- treating projection readiness as operational approval

## Recommended Consumer Adapter Steps

1. Fetch the endpoint response.
2. Confirm HTTP 200 for successful reads.
3. Confirm JSON content type.
4. Confirm required governance flags are true.
5. Render only fields needed by the client.
6. Ignore unknown optional fields.
7. Route any operational action to Inventory-owned workflows.

## Governance Flag Check

Consumers should check these fields at the top-level response where available:

```text
advisory_only == true
read_only == true
inventory_source_of_truth_preserved == true
```

If any flag is missing or false, the consumer should fail closed and avoid rendering the payload as trusted operational guidance.

## Example Dashboard Adapter

```python
def load_review_dashboard(http_client):
    response = http_client.get('/forecast/decision-review/dashboard')
    if response.status_code != 200:
        raise RuntimeError('Decision review dashboard unavailable')

    payload = response.json()
    if payload.get('advisory_only') is not True:
        raise RuntimeError('Unexpected non-advisory forecast payload')
    if payload.get('read_only') is not True:
        raise RuntimeError('Unexpected non-read-only forecast payload')
    if payload.get('inventory_source_of_truth_preserved') is not True:
        raise RuntimeError('Inventory source-of-truth guardrail missing')

    dashboard = payload['dashboard']
    return {
        'response_version': payload['response_version'],
        'total_count': dashboard['summary']['total_count'],
        'ready_count': dashboard['summary']['ready_count'],
        'pending_count': dashboard['summary']['pending_count'],
        'items': dashboard['snapshot']['items'],
    }
```

## Example Export Adapter

```python
def load_review_export_bundle(http_client):
    response = http_client.get('/forecast/decision-review/export')
    if response.status_code != 200:
        raise RuntimeError('Decision review export bundle unavailable')

    payload = response.json()
    if payload.get('read_only') is not True:
        raise RuntimeError('Unexpected writable export payload')

    return {
        'bundle_version': payload['bundle_version'],
        'ready_for_delivery': payload['ready_for_delivery'],
        'record_count': payload['manifest']['record_count'],
        'valid': payload['validation']['valid'],
        'warnings': payload['validation']['warnings'],
    }
```

## Error Handling

Unsupported export formats return HTTP 400.

Example:

```http
GET /forecast/decision-review/export?export_format=csv
```

Expected body:

```json
{
  "detail": "Unsupported decision review export format"
}
```

Consumers should present this as a validation issue, not as an operational failure.

## Compatibility Expectations

Consumers should rely on:

- stable endpoint paths
- documented required fields
- version fields
- governance flags
- documented HTTP status codes

Consumers should not rely on:

- exact key ordering
- absence of optional fields
- fixed generated timestamps
- undocumented nested fields

## Operational Boundary

Forecasting owns read-only projections.

Inventory owns operational mutation.

Any future workflow that creates stock movements, purchase orders, approvals, or ledger changes must be implemented and governed by Inventory, not by these forecasting endpoints.

## Phase 9F Lock

Phase 9F is locked as a consumer handoff documentation phase.

It does not:

- add new endpoint behavior
- change existing endpoint behavior
- add mutation paths
- add new forecasting logic
- write files
- transmit export data
- override Inventory as source of truth
