# Program G7 — Executive Intelligence Brief

Program G7 composes the existing enterprise summary, health classification, portfolio risk signals, and an optional certified comparison into one tenant-isolated executive view.

## API

`GET /v1/intelligence/enterprise/brief?as_of_utc=...&baseline_as_of_utc=...`

`baseline_as_of_utc` is optional. When supplied, the brief includes the existing G6 comparison against the current `as_of_utc` state.

## Locked boundaries

The brief does not recalculate certified metrics, generate recommendations, rank or select models, predict outcomes, persist comparisons, or perform operational actions. Existing G1–G6 contracts remain unchanged.
