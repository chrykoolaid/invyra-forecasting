# Program H2 — Read-Only Operational Portfolio API

## Purpose

Program H2 exposes the certified H1 operational forecast portfolio summary through a tenant-isolated GET-only endpoint backed by the existing durable Program C forecast-history repository.

## Endpoint

`GET /v1/intelligence/operational/portfolio/summary`

Optional query parameter:

- `as_of_utc` — an ISO-8601 timestamp with a UTC offset. When omitted, the current UTC timestamp is used.

## Response

The endpoint returns the unchanged H1 summary data through the standard production response envelope, including item, location, item-location, evidence, snapshot, model-usage, history-reference, and evidence-reference coverage.

## Corrective Prerequisite

Before public exposure, H2 closes the H1 nested-immutability review finding by storing model-usage distribution as immutable ordered pairs while preserving the public serialized object shape.

## Locked Boundaries

H2 does not recalculate forecasts, infer live inventory state, classify stock risk, rank items or locations, recommend actions, create another persistence model, or add any write endpoint.

Forecasting remains advisory-only and read-only. Inventory remains the operational source of truth. No inventory, stock movement, purchase-order, lifecycle, history, or evidence mutation is introduced.
