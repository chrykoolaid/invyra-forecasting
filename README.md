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
- Adaptive model ranking evidence

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
- Forecasting remains read-only.
- Inventory ledger remains the source of truth.
- The engine does not mutate stock.
- The engine does not create stock movements.
- The engine does not create purchase orders.
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
```

## Phase 7A Adaptive Model Ranking

Phase 7A upgrades model selection from fixed performance weighting to adaptive, context-aware model ranking.

The selector now ranks eligible models using configurable evidence factors:

- historical accuracy
- recent accuracy and evaluation recency
- calibration
- stability
- bias control
- evaluation depth
- item/category/location/context fit
- forecast horizon fit
- seasonal fit
- data sufficiency
- drift resilience

Adaptive ranking remains advisory-only and read-only. It never mutates inventory, creates stock movements, creates or approves purchase orders, or overrides ledger truth.

Ranking decisions include:

- candidate model scores
- score components
- rationale and warnings
- ranking configuration version
- audit-safe selection record
- read-only/source-of-truth guardrail flags
