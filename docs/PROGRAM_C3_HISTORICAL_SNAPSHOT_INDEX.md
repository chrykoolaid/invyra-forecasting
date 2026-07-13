# Program C3 — Historical Snapshot Index

## Purpose

Program C3 introduces an internal, tenant-isolated index over immutable forecast history records.

The index supports read-only lookup by:

- history identifier
- snapshot identifier
- forecast identifier
- history version number
- exact UTC timestamp
- inclusive UTC time range

## Boundaries

The index does not modify forecasts, history records, snapshots, evidence, metrics, review context, or evaluation records.

It introduces no public API, filesystem persistence, database persistence, authentication, or authorization.

## Isolation

All indexed records are partitioned by the active request namespace. Identical history, snapshot, and forecast identifiers may exist independently in separate tenant namespaces.

## Timestamp Requirements

Indexed timestamps must be valid ISO-8601 values with an explicit UTC offset. Query ranges are inclusive.

## Guardrails

Forecasting remains advisory-only and read-only. Inventory remains the operational source of truth.
