# Program G4 — Enterprise Forecast Health Classification

## Purpose

Program G4 adds a deterministic, explainable portfolio-health classification derived from the certified G3 enterprise intelligence summary.

## Classification

The policy reports one of: `unavailable`, `limited`, `developing`, `healthy`, or `strong`.

It uses only evaluated portfolio coverage, certified weighted accuracy, and certified weighted calibration gap. Every result includes fixed classification reasons and the underlying evidence references.

## API

`GET /v1/intelligence/enterprise/health`

The existing G2/G3 summary endpoint remains unchanged.

## Locked Boundaries

- No model scoring, ranking, selection, or recommendation.
- No anomaly detection or operational action.
- No metric recalculation beyond deterministic portfolio ratios and threshold comparison.
- No write endpoint or lifecycle mutation.
- Forecasting remains advisory-only and read-only.
- Inventory remains the operational source of truth.
