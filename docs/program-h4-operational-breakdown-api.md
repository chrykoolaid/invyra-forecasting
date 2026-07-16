# Program H4 — Read-Only Item and Location Breakdown API

## Purpose

H4 exposes the immutable H3 item, location, and item-location breakdown through the existing operational portfolio API surface.

## Endpoint

`GET /v1/intelligence/operational/portfolio/breakdown`

The optional `as_of_utc` query parameter provides reproducible historical reads. The endpoint uses the existing tenant-isolated durable Program C forecast-history repository and the unchanged H3 aggregation service.

## Response

The response includes deterministic breakdown entries for:

- items;
- locations;
- item-location pairs.

Each entry preserves forecast-history counts, evidence-linked and snapshot-linked counts, earliest and latest included timestamps, history references, and evaluation-evidence references.

## Locked Boundaries

H4 adds no write endpoint or persistence model. It does not recalculate forecasts, read or infer live inventory quantities, calculate accuracy, classify stock risk, detect anomalies, rank items or locations, recommend actions, or mutate inventory, stock, purchasing, lifecycle, history, or evidence state.

Forecasting remains advisory-only, read-only, tenant-isolated, evidence-backed, and preserves Inventory as the operational source of truth.
