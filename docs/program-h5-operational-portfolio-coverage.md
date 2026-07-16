# Program H5 — Operational Portfolio Coverage Classification

## Purpose

H5 adds a deterministic, explainable classification of forecast-history evidence coverage using the existing H1 operational summary and H3 item/location breakdown contracts.

The classification describes only how completely included forecast-history records are linked to evaluation evidence and forecast snapshots.

## Coverage States

- `unavailable`: no forecast-history records are available;
- `limited`: the lower linkage ratio is below 50%;
- `developing`: the lower linkage ratio is at least 50% but below 80%;
- `established`: the lower linkage ratio is at least 80% but below 100%;
- `complete`: both evaluation-evidence and snapshot linkage cover every included history record.

The lower of the two linkage ratios controls the status. Every non-empty assessment preserves the observed ratios and provides fixed plain-language reasons.

## Input Integrity

H5 requires the H1 summary and H3 breakdown to share:

- the same tenant namespace;
- the same `as_of_utc` boundary;
- advisory-only and read-only governance;
- matching item, location, item-location, and history-reference coverage.

## Locked Boundaries

H5 does not inspect live inventory, calculate forecast quality or accuracy, classify stockout or overstock risk, detect anomalies, rank items or locations, recommend actions, or mutate any inventory, stock, purchase-order, lifecycle, history, or evidence state.

No API or persistence model is introduced in H5.
