# Program C — History Platform Certification

## Certified Scope

Program C establishes a tenant-isolated, immutable, append-only forecast history platform covering:

- immutable history records
- forecast version lineage
- historical snapshot indexing
- archived explainability and evidence
- dependency-injected read models
- local file-backed history persistence
- local file-backed explainability persistence
- durable provider reconstruction after restart
- stable read-only FastAPI endpoints
- root application registration and API metadata

## Certified Guarantees

1. History records are immutable after creation.
2. Version chains require direct parent-child sequencing.
3. Duplicate history identifiers and duplicate forecast versions are rejected within a tenant namespace.
4. History, explainability, indexes, and API reads are tenant-isolated.
5. The default namespace remains backward compatible with predictable local storage paths.
6. Durable history and explainability survive provider reconstruction and process restart.
7. Historical explanations and evidence references are preserved as generated.
8. History endpoints expose GET operations only.
9. Responses retain stable production envelopes and advisory/read-only guardrails.
10. Inventory remains the operational source of truth.

## Public Read Surface

- `GET /v1/history`
- `GET /v1/history/{history_id}`
- `GET /v1/history/{history_id}/lineage`
- `GET /v1/history/forecasts/{forecast_id}/versions`

No history creation, mutation, amendment, deletion, inventory write, stock movement, or purchase-order endpoint is exposed.

## Known Boundaries

This certification covers the current local/server-first implementation. It does not certify:

- external authentication or authorization
- tenant provisioning or billing
- distributed databases or cross-process locking
- cloud replication
- retention and archival policies
- cryptographic signing or tamper-evident storage

Those concerns belong to later operational-hardening programs.

## Certification Result

Program C is complete when the C11 cross-layer certification tests and the full GitHub CI workflow pass and the certification PR is merged into `main`.
