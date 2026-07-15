# Program G1 — Enterprise Forecast Intelligence Summary

## Purpose

Program G1 introduces the smallest enterprise intelligence aggregation layer over the certified Program F foundation.

It combines tenant-scoped F1 model registry metadata, F2 certified performance statistics, F3 confidence governance, and explicit evidence references into one immutable portfolio summary.

## Summary content

- registered model-version and horizon count
- evaluated model-version count
- total eligible evaluation evidence count
- confidence-status distribution
- evaluation-count-weighted average accuracy
- evaluation-count-weighted average calibration gap
- deterministic per-model intelligence records
- explicit evidence references and as-of timestamp

Weighted portfolio metrics use only existing certified F2 values and their eligible evaluation counts. Models without certified evaluations remain visible but do not invent portfolio metrics.

## Governance

- Active tenant namespace must match every registry input.
- Registry, statistics, confidence, horizon, and evidence counts must match.
- Evaluated models require explicit evidence references.
- Inputs and outputs remain immutable, advisory-only, read-only, and Inventory-source-of-truth preserving.
- The service does not score, rank, select, recommend, retrain, tune, retire, or mutate models.
- No API, persistence, forecast-generation, inventory, stock, or purchase-order behavior changes are introduced.

## Scope boundary

G1 is a domain-level summary foundation only. A public enterprise-intelligence API, dashboard, anomaly detector, category aggregation, or executive recommendation layer requires a later separately scoped Program G increment after this contract is certified by CI.
