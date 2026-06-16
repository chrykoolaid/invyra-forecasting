# Confidence Recalibration — Phase 1F

Phase 1F connects historical forecast accuracy back into confidence scoring.

The engine now uses recent item/location accuracy results to adjust the confidence generated from movement history and supplier data.

## Purpose

Confidence must be earned. A forecast may have clean input data but still perform poorly over time. Phase 1F introduces the first feedback loop so confidence reflects both input quality and historical forecast performance.

## Inputs

The recalibration layer uses recent accuracy records from:

```text
data/snapshots/accuracy_events.jsonl
```

The default read window is controlled by:

```text
INVYRA_CONFIDENCE_ACCURACY_WINDOW=10
```

## Phase 1F Rules

- No accuracy history: confidence remains unchanged.
- Average accuracy >= 85: confidence receives a small uplift.
- Average accuracy between 65 and 85: confidence is mostly unchanged.
- Average accuracy < 65: confidence is reduced.
- Three recent low-accuracy records: confidence is reduced further.
- Repeated over-forecast or under-forecast bias: confidence is reduced.

## Governance

- Recalibration must not hide the original low-confidence warning.
- Recalibration must explain why confidence changed.
- Recalibration must not mutate inventory, purchasing, or audit records.
- Accuracy-informed confidence remains advisory.
- The inventory ledger remains the source of truth.

## Future Hardening

Future phases should add model-level confidence calibration, category-level benchmarks, supplier-adjusted confidence, expiry-sensitive confidence, seasonality-aware confidence, and dashboard reporting for confidence drift.
