# Program G2 — Enterprise Intelligence API

## Purpose

Program G2 exposes the certified Program G1 enterprise forecast intelligence summary through one tenant-scoped, GET-only API resource:

- `GET /v1/intelligence/enterprise/summary`

The endpoint uses the existing tenant context, request-correlation metadata, production response envelope, and durable Program F1 model-performance registry.

## Current evidence boundary

The runtime currently has durable F1 registry storage but no separately certified durable F2 statistics store. G2 therefore reports registered model versions with an honest `experimental` evidence status and zero eligible evaluations until certified statistics are connected by a later approved slice.

No accuracy, calibration, bias, evidence count, or confidence maturity is invented. Missing registry data returns a valid empty portfolio summary.

Clients may supply `as_of_utc` for reproducible reads. Invalid timestamps return HTTP 400.

## Governance

- GET-only and tenant-isolated.
- Advisory-only and read-only.
- Inventory remains the operational source of truth.
- No model score, rank, selection, recommendation, retraining, tuning, retirement, or lifecycle mutation.
- No inventory, stock, purchase-order, history, evaluation, or registry mutation.
- Existing application entrypoint and locked history routes remain unchanged.
