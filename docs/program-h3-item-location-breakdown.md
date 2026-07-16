# Program H3 — Item and Location Portfolio Breakdown

## Purpose

H3 extends the certified operational portfolio foundation with deterministic breakdowns across item, location, and item-location dimensions using existing immutable Program C forecast-history records.

H3 is domain-only. It adds no public endpoint and no persistence model.

## Delivered Views

Each breakdown entry reports:

- forecast-history record count;
- evidence-linked record count;
- snapshot-linked record count;
- earliest and latest included forecast timestamps;
- explicit history references;
- explicit evaluation-evidence references.

The complete result contains immutable, deterministically ordered item, location, and item-location collections and supports reproducible `as_of_utc` filtering.

## Locked Boundaries

H3 does not read or infer live inventory quantities, calculate forecast accuracy, classify stock risk, detect anomalies, rank items or locations, recommend replenishment, recalculate forecasts, or introduce operational actions.

The breakdown remains advisory-only, read-only, tenant-namespaced, evidence-backed, and preserves Inventory as the operational source of truth.

## Next-Slice Rule

A later Program H slice may expose these breakdowns through GET-only APIs after H3 passes the full pytest suite, deployment-readiness validation, and Render blueprint validation.
