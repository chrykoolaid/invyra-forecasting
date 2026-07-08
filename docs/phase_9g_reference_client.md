# Phase 9G — Read-Only Reference Client

## Status

Phase 9G adds a small read-only reference client for downstream consumers of the Forecast Decision Review API.

The reference client is an integration helper only. It does not add runtime API behavior or operational authority.

## Module

```text
src/invyra_forecasting/decision_review_client.py
```

## Purpose

The reference client helps approved consumers:

- fetch the decision review dashboard projection
- fetch the decision review export bundle projection
- validate read-only governance flags
- parse stable downstream-friendly views
- fail closed on unexpected response status or missing guardrails

## Read-Only Client Surface

```python
from invyra_forecasting.decision_review_client import DecisionReviewReferenceClient

client = DecisionReviewReferenceClient(http_client)
dashboard = client.get_dashboard()
export = client.get_export_bundle(export_format="json")
```

The supplied `http_client` must provide a minimal `get(path, **kwargs)` method returning an object with:

- `status_code`
- `json()`

This keeps the reference client dependency-light and usable with multiple HTTP clients or test clients.

## Parsed Views

### Dashboard View

```python
DecisionReviewDashboardView(
    response_version="8H.1",
    total_count=1,
    ready_count=1,
    pending_count=0,
    needs_more_evidence_count=0,
    items=(...),
)
```

### Export Bundle View

```python
DecisionReviewExportBundleView(
    bundle_version="8L.1",
    export_version="8I.1",
    export_format="json",
    ready_for_delivery=True,
    record_count=1,
    valid=True,
    warnings=(),
)
```

## Governance Validation

The client checks:

```text
advisory_only == true
read_only == true
inventory_source_of_truth_preserved == true
```

If any guardrail is missing or false, the client raises `DecisionReviewClientError`.

## Error Handling

The client fails closed when:

- HTTP status is not the expected status
- the response body is not a dictionary
- required response fields are missing or incorrectly typed
- governance flags are absent or false

## Compatibility

The client ignores unknown optional fields and parses only the stable fields needed by downstream consumers.

## Guardrails

Phase 9G preserves the locked API boundary:

- advisory-only
- read-only
- no new forecasting logic
- no inventory mutation
- no stock movement creation
- no purchase order creation or approval
- no export file writing
- no export data transmission
- Inventory remains source of truth

## Tests

Coverage is provided by:

```text
tests/test_phase_9g_decision_review_client.py
```
