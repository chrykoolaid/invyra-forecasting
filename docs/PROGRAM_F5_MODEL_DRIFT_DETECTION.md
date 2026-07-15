# Program F5 — Model Drift Detection

## Purpose

Compare two certified Program F2 performance-statistics windows for the same registered model version and forecast horizon, then produce an explainable advisory drift classification.

## States

- `insufficient_evidence`
- `stable`
- `watch`
- `drift_detected`

The default policy observes changes in average accuracy, absolute bias, and calibration gap. Both windows require at least 10 certified evaluations and complete metrics.

## Boundaries

F5 does not change model lifecycle state, ranking scores, selector inputs, forecast behaviour, parameters, or persisted evidence. It does not retrain, tune, retire, disable, or select models. All assessments remain advisory-only and read-only, and Inventory remains the operational source of truth.
