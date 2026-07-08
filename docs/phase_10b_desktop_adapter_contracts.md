# Phase 10B — Desktop Adapter Contract Examples

## Status

Phase 10B defines concrete read-only adapter contract examples for future Invyra Desktop consumption of the locked Phase 9 Forecast Decision Review API.

This phase is documentation and readiness verification only.

It does not add desktop runtime behavior, forecasting logic, endpoint behavior, or operational authority.

## Adapter Purpose

A future Desktop adapter should translate read-only Forecast Decision Review API payloads into small UI-ready view models.

The adapter must not mutate Inventory or treat forecasts as operational truth.

## Approved Adapter Inputs

The Desktop adapter may consume only:

```http
GET /forecast/decision-review/dashboard
GET /forecast/decision-review/export
GET /forecast/decision-review/export?export_format=dict
```

The recommended implementation source is the existing read-only reference client:

```python
from invyra_forecasting.decision_review_client import DecisionReviewReferenceClient
```

## Dashboard Summary View Model

A future Desktop dashboard summary card may use this shape:

```python
@dataclass(frozen=True)
class DesktopForecastReviewSummaryCard:
    response_version: str
    total_count: int
    ready_count: int
    pending_count: int
    needs_more_evidence_count: int
    advisory_label: str = "Forecast advisory only"
    read_only: bool = True
```

Mapping source:

```text
DecisionReviewDashboardView.response_version
DecisionReviewDashboardView.total_count
DecisionReviewDashboardView.ready_count
DecisionReviewDashboardView.pending_count
DecisionReviewDashboardView.needs_more_evidence_count
```

## Export Preview View Model

A future Desktop export preview panel may use this shape:

```python
@dataclass(frozen=True)
class DesktopForecastExportPreview:
    bundle_version: str
    export_version: str
    export_format: str
    ready_for_delivery: bool
    record_count: int
    valid: bool
    warning_count: int
    advisory_label: str = "Export projection only"
    read_only: bool = True
```

Mapping source:

```text
DecisionReviewExportBundleView.bundle_version
DecisionReviewExportBundleView.export_version
DecisionReviewExportBundleView.export_format
DecisionReviewExportBundleView.ready_for_delivery
DecisionReviewExportBundleView.record_count
DecisionReviewExportBundleView.valid
len(DecisionReviewExportBundleView.warnings)
```

## Adapter Guardrail Contract

A future Desktop adapter must:

- validate `advisory_only == true`
- validate `read_only == true`
- validate `inventory_source_of_truth_preserved == true`
- ignore unknown optional fields
- fail closed on invalid governance flags
- fail closed on invalid required field types
- display forecast data as advisory only
- route all operational actions to Inventory-owned services

## Adapter Must Not

The Desktop adapter must not:

- create stock movements
- create purchase orders
- approve purchase orders
- mutate Inventory
- update the stock ledger
- write export files from the forecasting engine
- transmit export data from the forecasting engine
- convert forecast projections into operational truth

## Example Dashboard Adapter Flow

```python
def load_desktop_forecast_summary(reference_client):
    view = reference_client.get_dashboard()
    return DesktopForecastReviewSummaryCard(
        response_version=view.response_version,
        total_count=view.total_count,
        ready_count=view.ready_count,
        pending_count=view.pending_count,
        needs_more_evidence_count=view.needs_more_evidence_count,
    )
```

## Example Export Adapter Flow

```python
def load_desktop_export_preview(reference_client):
    view = reference_client.get_export_bundle(export_format="json")
    return DesktopForecastExportPreview(
        bundle_version=view.bundle_version,
        export_version=view.export_version,
        export_format=view.export_format,
        ready_for_delivery=view.ready_for_delivery,
        record_count=view.record_count,
        valid=view.valid,
        warning_count=len(view.warnings),
    )
```

## UI Behavior Contract

Desktop UI should show:

- forecast review unavailable if the API is down
- advisory-only labels on all forecast surfaces
- validation warnings as informational
- no operational buttons sourced from forecasting responses
- no automatic Inventory action from forecast projection data

## Phase 10B Lock

Phase 10B is locked as adapter contract examples only.

It preserves:

- advisory-only
- read-only
- no runtime behavior changes
- no endpoint behavior changes
- no desktop runtime implementation
- no new forecasting logic
- no inventory mutation
- no stock movement creation
- no purchase order creation
- no purchase order approval
- no export file writing
- no export data transmission
- Inventory remains source of truth
