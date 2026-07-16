# Program G5 — Explainable Portfolio Risk Signals

## Purpose

Program G5 exposes deterministic, evidence-backed portfolio conditions derived from the certified G4 health view.

## Signals

- no certified evidence;
- low evaluated coverage;
- incomplete certified quality metrics;
- weighted accuracy below the healthy threshold;
- weighted calibration gap above the healthy threshold.

## API

`GET /v1/intelligence/enterprise/risks`

## Locked Boundaries

G5 does not perform predictive anomaly detection, model drift comparison, model scoring, ranking, selection, recommendations, lifecycle changes, inventory mutation, stock mutation, or purchasing action.

Signals are read-only observations with fixed thresholds, observed values, reasons, and evidence references. The existing G1–G4 contracts remain unchanged.
