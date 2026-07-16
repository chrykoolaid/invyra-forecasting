# Program H7 — Operational Portfolio Evidence Signals

## Mission

Report deterministic, explainable conditions observed in the certified operational forecast-history portfolio.

## Inputs

H7 consumes only the existing immutable outputs from:

- H3 operational item/location breakdowns;
- H5 operational coverage classification.

## Signals

H7 may report:

- `no_history`;
- `missing_evidence_linkage`;
- `incomplete_evidence_linkage`;
- `missing_snapshot_linkage`;
- `incomplete_snapshot_linkage`;
- `uneven_item_history_distribution`;
- `uneven_location_history_distribution`.

Linkage signals describe missing or incomplete references. Distribution signals state only that included record counts differ across a dimension. They do not classify the difference as good, bad, risky, anomalous, or actionable.

## Locked boundaries

H7 does not:

- read or infer live inventory quantities;
- calculate or recalculate forecasts;
- calculate forecast accuracy or model quality;
- classify stockout, overstock, or purchasing risk;
- run anomaly detection or future prediction;
- rank items, locations, or models;
- recommend or execute operational actions;
- add a public endpoint or persistence model;
- mutate inventory, stock, purchase orders, lifecycle state, history, or evidence.

Forecasting remains advisory-only and read-only. Inventory remains the operational source of truth.
