# Forecast Accuracy Tracking — Phase 1E

Phase 1E adds the first proof layer for forecast quality.

The engine can now accept actual demand records, compare them against a forecast quantity, calculate simple baseline accuracy metrics, persist the result, and expose item-level accuracy readback.

## Purpose

Forecasting must be measurable. A Fortune 500-grade foundation needs traceability not only for what the engine predicted, but also for how the prediction performed later.

Phase 1E remains intentionally simple and explainable.

## Metrics

The baseline metrics are:

- Forecast quantity
- Actual quantity
- Error
- Absolute error
- Percentage error
- MAE-style single-evaluation value
- MAPE-style single-evaluation value
- Accuracy score
- Accuracy rating
- Bias classification

## Accuracy Rating

```text
High   = accuracy score >= 85
Medium = accuracy score >= 65 and < 85
Low    = accuracy score < 65
```

## Bias Classification

```text
On Target      = within 5% of actual demand
Over Forecast  = forecast quantity is above actual demand
Under Forecast = forecast quantity is below actual demand
No Actual Demand = actual demand is zero and forecast is also zero
```

## Persistence

Accuracy evaluations are stored as JSON Lines in:

```text
data/snapshots/accuracy_events.jsonl
```

The path can be changed with:

```text
INVYRA_ACCURACY_LOG_PATH
```

## API Routes

```text
POST /accuracy/evaluate
GET /accuracy/item/{item_id}
```

## Governance Rules

- Accuracy tracking is evidence, not operational stock truth.
- Actuals must include item, location, date, quantity, and environment.
- Actuals must match the requested item, location, and environment.
- Accuracy tracking must not mutate inventory, purchasing, audit, or forecast snapshots.
- Low accuracy should be shown honestly and should feed future confidence improvements.

## Future Hardening

Future phases should add rolling accuracy windows, model-level accuracy, SKU/category/location benchmarks, forecast accuracy reports, confidence recalibration, and model governance dashboards.
