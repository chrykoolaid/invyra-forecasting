# Program I4 — Read-Only Decision Review API

## Scope

Program I4 exposes the certified Program I1–I3 decision-intelligence chain through:

`GET /v1/intelligence/decisions/review`

The endpoint composes existing enterprise and operational intelligence at one reproducible `as_of_utc` boundary, then returns:

- decision context;
- deterministic priority;
- human-readable explanation.

## Governance

The endpoint is tenant-isolated through the existing tenant middleware and repositories. It is GET-only, advisory-only, and read-only. Inventory remains the source of truth.

## Exclusions

Program I4 does not add persistence, forecast recalculation, scoring, ranking, recommendations, predictions, inventory inference, purchasing actions, or mutation of inventory, stock, evidence, or history.
