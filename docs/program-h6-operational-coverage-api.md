# Program H6 — Read-Only Operational Coverage API

## Purpose

Expose the certified H5 operational portfolio coverage assessment through a tenant-isolated, GET-only production API.

## Endpoint

`GET /v1/intelligence/operational/portfolio/coverage`

Optional query parameter:

- `as_of_utc`: timezone-aware ISO-8601 timestamp used as the reproducible history boundary.

## Inputs

The endpoint reuses the existing durable tenant forecast-history repository and derives:

1. the H1 operational portfolio summary;
2. the H3 item/location breakdown; and
3. the unchanged H5 coverage assessment.

No separate coverage persistence is introduced.

## Output

The standard production envelope contains:

- coverage status;
- forecast-history and dimensional counts;
- evaluation-evidence and snapshot linkage counts;
- observed coverage ratios;
- fixed explanatory reasons;
- history and evaluation-evidence references;
- advisory-only, read-only, and Inventory source-of-truth flags.

## Locked boundaries

H6 does not:

- recalculate forecasts;
- calculate forecast accuracy or quality;
- infer live inventory state;
- classify stockout or overstock risk;
- detect anomalies;
- rank items or locations;
- recommend actions;
- add a write endpoint or persistence model;
- mutate inventory, stock, purchase orders, lifecycle state, history, or evidence.

The endpoint remains tenant-isolated, evidence-backed, reproducible, advisory-only, and read-only.
