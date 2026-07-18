# Program I1 — Decision Context Foundation

## Mission

Compose existing certified enterprise and operational intelligence into one immutable, explainable context for human review.

## Certified inputs

I1 consumes existing outputs from Programs G and H:

- enterprise intelligence summary;
- enterprise health classification;
- enterprise portfolio risk signals;
- operational portfolio summary;
- operational coverage classification;
- operational evidence signals.

## Delivered contract

The decision context preserves:

- tenant namespace;
- reproducible `as_of_utc` boundary;
- each certified input as a separate source section;
- consolidated, sorted and deduplicated evidence references;
- consolidated, sorted and deduplicated forecast-history references;
- advisory-only, read-only and Inventory source-of-truth governance.

## Locked boundaries

I1 does not:

- calculate or recalculate forecasts or metrics;
- score, rank, prioritize or select items, locations or models;
- create recommendations or predictions;
- infer live inventory or stock risk;
- trigger workflows or operational actions;
- add a public API or persistence model;
- mutate inventory, stock, purchase orders, lifecycle state, history or evidence.

The service exposes only `compose`. Forecasting remains advisory-only and read-only. Inventory remains the operational source of truth.
