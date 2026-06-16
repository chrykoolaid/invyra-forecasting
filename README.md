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

Phase 1 routes:

- `GET /health`
- `POST /forecasts/item`
- `POST /forecasts/batch`
- `POST /risk/stockout`
- `POST /recommendations/reorder`
- `GET /snapshots/{snapshot_id}`
- `GET /audit/events`
- `POST /audit/override`
- `POST /accuracy/evaluate`
- `GET /accuracy/item/{item_id}`

The forecast, risk, and reorder endpoints call the real Python forecasting service through typed API payload contracts. Snapshot, audit, accuracy, and confidence recalibration foundations provide traceability and proof of forecast quality.

## API Examples

Ready-to-use request fixtures live under `data/sample/api/`.

Module-specific fixtures live under `integrations/*/fixtures/` for Inventory, ScanOps, Reorder Review, Purchasing, Dashboard, Reports, Suppliers, Markdowns, Wastage, POS, and CRM.

Curl and PowerShell examples live under `examples/api/`.
