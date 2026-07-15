# Program G3 — Durable Certified Statistics Read Integration

## Purpose

Program G3 connects the existing G2 enterprise intelligence endpoint to immutable, precomputed Program F2 model-performance statistics without recalculating evaluation metrics during API reads.

## Delivered capability

- immutable certified-statistics snapshot records
- append-only in-memory and JSONL repositories
- tenant-isolated reconstruction after restart
- explicit evaluation-evidence references
- latest certified snapshot selection by registered model and forecast horizon
- tenant-safe joins to the durable F1 model registry
- F3 confidence classification from the loaded certified statistics
- unchanged G2 endpoint and response envelope

The endpoint continues to return an experimental zero-evidence summary for registered models that do not yet have a certified statistics snapshot.

## Certification boundary

G3 stores and reads statistics that were already calculated by the locked F2 service from E7-eligible evaluation evidence. It does not calculate MAE, RMSE, MAPE, bias, accuracy, calibration, or confidence metrics itself.

Every non-empty statistics snapshot requires explicit evidence references. Registry, model-version, forecast-horizon, tenant, and enterprise-guardrail compatibility are validated before the snapshot contributes to an enterprise summary.

## Preserved boundaries

- No public write endpoint.
- No evaluation ingestion or metric recalculation.
- No model scoring, ranking, selection, recommendation, retraining, tuning, retirement, or lifecycle transition.
- No inventory, stock movement, purchase-order, forecast-history, or evaluation mutation.
- Forecasting remains advisory-only and read-only.
- Inventory remains the operational source of truth.
