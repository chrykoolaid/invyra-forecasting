# Invyra Forecasting Engine

Python-first explainable forecasting intelligence layer for the Invyra ecosystem.

This is the Phase 1 baseline for the Invyra Forecasting Engine. It follows the locked direction: **Fortune 500-grade foundation, phased commercial implementation**.

## Phase 1 Scope

Phase 1 focuses on Inventory, ScanOps, Reorder Review, Purchasing, Suppliers, Dashboard, and Reports.

Phase 1 deliberately excludes advanced ML, external APIs, auto-purchasing, CRM forecasting, finance forecasting, customer-level prediction, and enterprise optimization.

## Product Principle

**Make it smarter, not harder.**

Forecasting must assist decisions without cluttering staff workflows or replacing the inventory ledger.

## Outputs

- Demand forecast per item/location
- Days of cover
- Stockout risk
- Overstock risk
- Suggested reorder quantity
- Supplier lead-time impact
- Forecast confidence
- Forecast explanation
- Forecast snapshot
- Audit event
- Forecast accuracy evaluation
- Accuracy-informed confidence recalibration

## Governance

1. Forecasting is advisory, not the source of truth.
2. Inventory ledger remains the source of truth.
3. Forecasts include confidence.
4. Recommendations include explanations.
5. Manager overrides must be audit-logged.
6. Item + location level calculations are required.
7. LIVE / TRAINING / TEST separation is required.
8. No auto-purchasing in v1.
9. No fake AI claims in v1.
10. Start with simple explainable forecasting before advanced ML.

## Current Intelligence Status

The forecasting engine now supports a registry-backed intelligence path while preserving the original advisory forecasting guardrails.

Current locked guarantees:

- Forecasting remains advisory-only.
- Inventory ledger remains the source of truth.
- The engine does not mutate stock.
- The engine does not create stock movements.
- The engine does not create or approve purchase orders.
- Intelligence metadata is explainability context, not an operational write path.
- Base service forecast math remains separate from optional registry-backed intelligence helpers.

## Stable Service Import Paths

Base forecasting service:

```python
from invyra_forecasting.services import ForecastingService
```

Registry-backed intelligence helper:

```python
from invyra_forecasting.services import run_item_forecast_with_registry_intelligence
```

Direct compatibility paths remain supported:

```python
from invyra_forecasting.services.forecasting_service import ForecastingService
from invyra_forecasting.services.intelligence_forecasting import run_item_forecast_with_registry_intelligence
```

The package-level export is an integration convenience only. It does not couple the base `ForecastingService` implementation to registry internals.

## Phase 2U Forecast Signal Registry

The Forecast Signal Registry is the controlled intelligence boundary between Invyra modules and the forecasting engine.

Modules publish normalized forecast signals. The engine consumes those signals as advisory intelligence inputs.

The registry does not:

- mutate inventory
- create stock movements
- create purchase orders
- approve purchase orders
- replace the inventory ledger as source of truth

Initial package:

```text
src/invyra_forecasting/signals/
  schema.py
  validators.py
  registry.py
  normalizers.py
```

Initial supported signal categories include sales, stock movements, receiving, purchasing, supplier lead time, adjustments, wastage, markdowns, transfers, ScanOps gap/floor/shelf events, and location stock snapshots.

## Phase 2V Forecast Intelligence Pipeline

The Forecast Intelligence Pipeline transforms registered signals into model-ready intelligence objects before any forecasting model receives them.

Pipeline stages:

```text
Forecast Signal Registry
        |
        v
Signal Ingestion
        |
        v
Signal Normalization Flow
        |
        v
Signal Quality Assessment
        |
        v
Signal Weighting
        |
        v
Feature Extraction
        |
        v
Evidence Linking
        |
        v
ForecastIntelligence object
        |
        v
Forecast Models
```

Core package:

```text
src/invyra_forecasting/intelligence/
  ingestion/collector.py
  normalization/pipeline.py
  validation/quality.py
  weighting/scorer.py
  features/extractor.py
  evidence/linker.py
  objects.py
  pipeline.py
```

The pipeline produces a `ForecastIntelligence` object containing:

- item and location identity
- environment boundary
- analysis window
- normalized signals
- quality assessments
- weighted signals
- extracted feature set
- evidence links
- confidence
- processing metadata
- audit references

Phase 2V remains advisory-only. It does not mutate inventory, create stock movements, create purchase orders, approve purchase orders, or replace the inventory ledger.

## Phase 2W Model Handoff Layer

The Model Handoff Layer converts `ForecastIntelligence` into stable model input/output contracts.

This phase adds:

```text
src/invyra_forecasting/models/
  contracts.py
  handoff.py
  baseline.py
  service.py
```

Flow:

```text
ForecastIntelligence
        |
        v
ForecastModelHandoffAdapter
        |
        v
ForecastModelInput
        |
        v
BaselineExplainableDemandModel
        |
        v
ForecastModelOutput
```

The Phase 2W baseline model is deterministic and explainable. It is not an advanced ML model and does not make fake AI claims. Future models can replace it while keeping the same handoff contract.

The model output remains advisory-only and does not mutate inventory, create stock movements, create purchase orders, approve purchase orders, or replace the inventory ledger.

## Phase 2X Intelligence Summary Adapter

The intelligence summary adapter creates compact, snapshot-friendly context from registry-backed intelligence results.

This phase adds:

```text
src/invyra_forecasting/intelligence_summary.py
```

The summary is designed for metadata and explainability. It does not change forecast math or recommendation decisions.

## Phase 2Y Snapshot Intelligence Context

Forecast snapshots support optional `intelligence_context` metadata.

The field is backward-compatible and defaults to `None` for existing callers.

## Phase 2Z Service Intelligence Context

`ForecastingService.run_item_forecast()` supports optional `intelligence_context` passthrough into forecast snapshots.

Default service behavior remains unchanged when no context is provided.

## Phase 3A Registry Intelligence Forecast Helper

Phase 3A adds a helper path that builds registry-backed intelligence context and passes it into the existing forecasting service.

The helper attaches intelligence context to snapshots while preserving base forecasting behavior.

## Phase 3B Intelligence Explanation Context

Phase 3B adds explanation helpers that convert intelligence context into readable drivers and warnings.

These helpers enrich explanations only through metadata. They do not change forecast math or recommendations.

## Phase 3C Helper Explanation Enrichment

Phase 3C wires the Phase 3B explanation enrichment into the registry-intelligence helper path.

The base forecasting service remains unchanged.

## Phase 3D Helper Contract Hardening

Phase 3D adds a safe helper contract test to keep the registry-intelligence helper importable and stable.

This is a test-only hardening pass with no production code changes.

## Phase 3E Governance Status Notes

Phase 3E documents the completed registry-backed intelligence path and its governance boundaries.

This is a documentation-only phase. It does not change runtime behavior, forecast calculations, recommendations, inventory, stock movements, or purchase-order behavior.

## Phase 3F Helper Separation Contract

Phase 3F adds a test-only separation contract confirming the base forecasting service does not import or directly depend on the registry-intelligence helper.

## Phase 3G Helper Advisory Guardrail Contract

Phase 3G adds a test-only advisory guardrail contract confirming the helper does not introduce stock mutation, stock movement creation, purchase-order creation, or purchase-order approval paths.

## Phase 3H Service Helper Export

Phase 3H exports the registry-intelligence helper from `invyra_forecasting.services` while preserving the direct helper import path.

This is an import convenience for future Base44/Desktop integration code. It does not change forecasting behavior.

## Phase 3I Service Import Compatibility

Phase 3I adds compatibility tests proving both package-level and direct import paths remain valid for the base forecasting service and registry-intelligence helper.

## Phase 3J Service Import Status Notes

Phase 3J documents the stable service import paths and updates the README status after Phase 3F through Phase 3I.

This is a documentation-only phase. It does not change runtime behavior, forecast calculations, recommendations, inventory, stock movements, or purchase-order behavior.

## Phase 3K README Phase Marker Contract

Phase 3K adds a test-only contract confirming README phase markers and stable service import path documentation remain present.

## Phase 3L Service Helper Boundary Contract

Phase 3L adds a test-only boundary contract confirming the registry-intelligence helper remains exported while its implementation stays isolated from the base forecasting service core module.

## Phase 3M Boundary Status Notes

Phase 3M documents Phase 3K and Phase 3L completion and keeps the public README aligned with helper-boundary governance.

This is a documentation-only phase. It does not change runtime behavior, forecast calculations, recommendations, inventory, stock movements, or purchase-order behavior.

## Phase 3N README Boundary Marker Contract

Phase 3N adds a test-only contract confirming README boundary status markers for Phase 3K through Phase 3M remain present.

## Phase 3O Phase 3N Status Notes

Phase 3O documents Phase 3N completion and keeps the README aligned with the latest documentation-boundary contract.

This is a documentation-only phase. It does not change runtime behavior, forecast calculations, recommendations, inventory, stock movements, or purchase-order behavior.
