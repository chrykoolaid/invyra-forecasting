# Phase 8A — Forecast Decision Gates

Phase 8A adds a read-only advisory decision gate layer for forecast outputs.

The gate evaluates whether a forecast is ready for operational review based on:

- confidence
- evidence references
- critical stockout risk confidence
- advisory-only status
- Inventory source-of-truth preservation

The gate does not:

- mutate inventory
- create stock movements
- create purchase orders
- approve purchase orders
- override ledger truth

The gate returns an audit-safe `ForecastDecisionGateResult` with reasons, warnings, configuration version, and governance metadata.
