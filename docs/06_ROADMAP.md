# Roadmap

## Phase 1 — Explainable Forecasting Baseline

Python package baseline, data contracts, validation, moving average models, weighted moving average model, trend adjustment, days of cover, stockout/overstock risk, reorder recommendation, confidence scoring, explanation builder, snapshot writer, audit logger, sample CSV data, demo script, unit tests, and optional FastAPI service.

## Phase 1B — API Payload Contracts + Endpoint Wiring

Typed FastAPI request contracts for item/location forecasts, batch forecasts, stockout risk, reorder recommendations, and override audit events.

The API layer must remain an integration wrapper. It must call the Python-first forecasting service and must not duplicate business logic inside endpoint handlers.

## Phase 1C — API Fixtures + Integration Examples

Sample JSON payloads, curl examples, PowerShell examples, module-specific integration fixtures, and tests that validate fixtures against the typed API contracts.

The goal is to make future Inventory, ScanOps, Reorder Review, Purchasing, Dashboard, and Reports integration predictable and low-risk.

## Phase 1D — Snapshot Retrieval + Audit Persistence

File-backed forecast snapshot repository, snapshot readback endpoint, JSONL audit event store, audit event readback endpoint, and persisted manager override audit events.

This phase strengthens traceability before deeper Inventory, Reorder Review, Purchasing, Dashboard, and Reports integration.

## Phase 1E — Forecast Accuracy Tracking Foundation

Forecast actuals input, forecast-vs-actual comparison, MAE/MAPE-style baseline metrics, accuracy scoring, JSONL accuracy event persistence, and API readback by item.

This phase starts the proof layer for forecast quality over time without introducing advanced ML or MLOps yet.

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
