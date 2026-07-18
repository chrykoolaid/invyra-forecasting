# Program I2 — Deterministic Decision Priority

## Purpose

Program I2 classifies the review-attention level of a certified Program I1 Decision Context using fixed, transparent precedence rules.

## Priority levels

- `high`
- `watch`
- `informational`
- `normal`

The policy does not calculate a score. It selects the highest applicable fixed level and returns only the reasons at that level.

## Fixed rules

- Elevated enterprise risk signals or limited operational coverage produce `high`.
- Watch enterprise signals, developing operational coverage, or watch operational evidence signals produce `watch`.
- Informational signals or unavailable operational coverage produce `informational` when no higher condition applies.
- A context with no applicable conditions produces `normal`.

## Governance boundaries

Program I2 is advisory-only, read-only, deterministic, evidence-backed, and tenant-preserving.

It does not:

- recalculate forecasts or metrics;
- rank items, locations, models, or tenants;
- generate recommendations;
- predict outcomes;
- infer inventory risk;
- create or approve purchase orders;
- mutate inventory, stock, evidence, or history;
- expose a public API;
- add persistence.
