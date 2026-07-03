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

## Phase 2X Advisory Forecast Orchestration

The Advisory Forecast Orchestration layer provides the first end-to-end forecasting service boundary.

It coordinates:

```text
Forecast Signal Registry
        |
        v
ForecastIntelligencePipeline
        |
        v
ForecastModelService
        |
        v
AdvisoryForecastResponse
```

This phase adds:

```text
src/invyra_forecasting/orchestration/
  contracts.py
  service.py
```

The orchestrator accepts an `AdvisoryForecastRequest` for one item/location/environment and returns an `AdvisoryForecastResponse` with:

- forecast quantity
- projected days of cover
- stockout risk
- confidence
- explanation
- evidence references
- intelligence summary
- model metadata
- advisory-only guardrails

The orchestration layer still does not mutate inventory, create stock movements, create purchase orders, approve purchase orders, or replace the inventory ledger.

## Phase 2Y Advisory API Wiring

The optional FastAPI wrapper exposes the advisory orchestration layer through:

```text
POST /advisory/forecast
```

The endpoint accepts an item/location/environment request plus normalized forecast signals. It builds an in-memory request-scoped registry, runs the advisory orchestration service, and returns the explainable forecast response.

This endpoint is stateless and does not persist signals. It does not mutate inventory, create stock movements, create purchase orders, approve purchase orders, or replace the inventory ledger.

## Phase 2Z Explainability Contracts

The Explainability package defines enterprise reporting contracts for future forecast explanation, confidence, evidence, diagnostics, and manager-readable narratives.

This first Phase 2Z pass adds contracts only:

```text
src/invyra_forecasting/explainability/
  objects.py
```

Initial explainability objects include:

- `EvidenceSummary`
- `ConfidenceBreakdown`
- `DiagnosticFinding`
- `DiagnosticReport`
- `RecommendationNarrative`
- `ForecastExplanation`

These contracts preserve advisory-only governance and provide the stable object model that later Phase 2Z passes will use for explanation builders, diagnostics, confidence reports, and enterprise recommendation summaries.

## Quick Start

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
python examples/run_local_demo.py
pytest
```

On macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
python examples/run_local_demo.py
pytest
```

## Optional API

The FastAPI layer is an integration wrapper. The core engine runs directly in Python without the API.

```bash
uvicorn invyra_forecasting.api.app:app --reload
```

Phase routes include:

- `GET /health`
- `POST /forecasts/item`
- `POST /forecasts/batch`
- `POST /risk/stockout`
- `POST /recommendations/reorder`
- `POST /advisory/forecast`
- `GET /snapshots/{snapshot_id}`
- `GET /audit/events`
- `POST /audit/override`
- `POST /accuracy/evaluate`
- `GET /accuracy/item/{item_id}`

The forecast, risk, reorder, and advisory endpoints call the real Python forecasting service through typed API payload contracts. Snapshot, audit, accuracy, and confidence recalibration foundations provide traceability and proof of forecast quality.

## API Examples

Ready-to-use request fixtures live under `data/sample/api/`.

Module-specific fixtures live under `integrations/*/fixtures/` for Inventory, ScanOps, Reorder Review, Purchasing, Dashboard, Reports, Suppliers, Markdowns, Wastage, POS, and CRM.

Curl and PowerShell examples live under `examples/api/`.
