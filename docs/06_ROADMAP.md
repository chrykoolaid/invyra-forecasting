# Roadmap

## Phase 1 — Explainable Forecasting Baseline

Python package baseline, data contracts, validation, moving average models, weighted moving average model, trend adjustment, days of cover, stockout/overstock risk, reorder recommendation, confidence scoring, explanation builder, snapshot writer, audit logger, sample CSV data, demo script, unit tests, and optional FastAPI service.

## Phase 1B — API Payload Contracts + Endpoint Wiring

Typed FastAPI request contracts for item/location forecasts, batch forecasts, stockout risk, reorder recommendations, and override audit events.

The API layer must remain an integration wrapper. It must call the Python-first forecasting service and must not duplicate business logic inside endpoint handlers.

## Phase 2 — Inventory Integration Hardening

Integrate with real Invyra Inventory item master and stock movement ledger. Add item details forecast section contracts, dashboard risk summaries, and audit-backed manager override workflow.

## Phase 3 — ScanOps + Reorder Review Integration

Gap Scan validation, Floor Scan interpretation, Reorder Review forecast reason column, and supplier lead-time refinement.

## Phase 4 — Purchasing + Supplier Reliability

Supplier delivery reliability scoring, draft PO support, supplier delay risk, and purchase urgency forecasting.

## Phase 5 — Multi-Location Foundation

Location-level forecast comparison, warehouse/branch planning support, and advisory transfer recommendation inputs.

## Phase 6 — Advanced Forecasting Readiness

Model registry, accuracy tracking, backtesting, feature store planning, and MLOps readiness.
