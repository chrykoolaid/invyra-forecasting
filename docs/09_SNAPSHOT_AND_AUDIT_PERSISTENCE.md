# Snapshot and Audit Persistence — Phase 1D

Phase 1D adds file-backed readback for forecast snapshots and audit events.

This is not a full enterprise persistence layer yet. It is a local, testable persistence foundation that gives the engine traceability before deeper Invyra module integration.

## Snapshot Repository

Forecast snapshots are stored as JSON files in:

```text
data/snapshots/
```

The default directory can be changed with:

```text
INVYRA_FORECAST_SNAPSHOT_DIR
```

Each snapshot is written to:

```text
{snapshot_id}.json
```

## Audit Store

Audit events are stored as JSON Lines in:

```text
data/snapshots/audit_events.jsonl
```

The default path can be changed with:

```text
INVYRA_AUDIT_LOG_PATH
```

Each line contains one audit event.

## API Routes

```text
GET /snapshots/{snapshot_id}
GET /audit/events
POST /audit/override
```

## Governance Rules

- Snapshots are read-only evidence of forecast outputs.
- Audit events are append-only in the local Phase 1D store.
- Manager overrides create audit events but do not change inventory stock.
- Reorder recommendations remain advisory and do not create purchase orders.
- LIVE / TRAINING / TEST remains attached to every persisted event.

## Future Hardening

Future phases should replace the local file store with durable application storage, retention policies, role permissions, event search indexing, and signed audit exports.
