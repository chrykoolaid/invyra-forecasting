# Program F6 — Model Retirement Governance

## Purpose

Produce an explainable, non-binding lifecycle recommendation from the immutable F1 registry entry, F3 confidence assessment, and F5 drift assessment.

## Recommendations

- `maintain`
- `move_to_observation`
- `deprecate`
- `retire`
- `retain_retired`

Drift escalation is limited to one governed lifecycle step at a time:

- experimental or active → observation
- observation → deprecated
- deprecated → retired

A watch signal may recommend moving an active model into observation. Stable or insufficient evidence does not justify escalation.

## Approval boundary

Every decision requires explicit approval and prohibits automatic transition. F6 does not update the append-only F1 registry, remove models, disable selector candidates, retrain models, tune parameters, or change forecast behavior.

Any actual lifecycle transition requires a separately scoped, audited action. Forecasting remains advisory-only and read-only, and Inventory remains the operational source of truth.
