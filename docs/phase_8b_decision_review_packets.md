# Phase 8B — Decision Review Packets

Phase 8B adds a read-only packet builder for forecast decision review.

The packet combines:

- forecast model output
- decision gate result
- evidence summary
- review notes
- governance metadata

The packet does not:

- mutate inventory
- create stock movements
- create purchase orders
- approve purchase orders
- override ledger truth

This layer is designed for future UI/API presentation of forecast review context without changing forecast math or operational records.
