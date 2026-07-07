# Phase 9E — Read-Only API Stability & Versioning

## Status

Phase 9E locks the compatibility policy for the Phase 9A Forecast Decision Review API surface.

This phase adds stability and versioning expectations for downstream clients. It does not add runtime behavior or new forecasting logic.

## Stable Endpoint Surface

The current read-only endpoint surface is:

```http
GET /forecast/decision-review/dashboard
GET /forecast/decision-review/export
GET /forecast/decision-review/export?export_format=dict
```

Unsupported export formats return a JSON validation response with HTTP 400.

## Current Stable Versions

The current response versions are:

- Dashboard API response: `8H.1`
- Export projection: `8I.1`
- Export bundle: `8L.1`

These versions describe the existing Phase 8 projection contracts exposed through Phase 9A endpoints.

## Compatibility Policy

Downstream clients may rely on:

- stable endpoint paths
- stable successful HTTP status code `200`
- stable unsupported export format HTTP status code `400`
- JSON response content type
- required governance flags at major response levels
- required version fields
- required summary, snapshot, export, manifest, and validation containers

Downstream clients should tolerate:

- additional optional fields
- additional metadata fields
- future versioned fields that do not remove existing required fields

Downstream clients should not require:

- exact key ordering
- exhaustive field lists
- a fixed `generated_at` value
- absence of future optional metadata

## Required Governance Flags

The following fields must remain present and true at major projection levels:

```text
advisory_only
read_only
inventory_source_of_truth_preserved
```

These flags are part of the compatibility contract and support safe downstream rendering.

## Backward-Compatible Changes

The following are considered backward-compatible:

- adding optional fields
- adding new metadata fields
- adding new supported export formats while preserving `json` and `dict`
- adding new response version metadata while preserving existing required fields
- adding new read-only endpoints outside the locked endpoint paths

## Breaking Changes

The following are considered breaking and require a separately scoped phase:

- removing required fields
- renaming required fields
- changing successful endpoint status codes
- changing unsupported format validation behavior without migration policy
- changing governance flags to false
- removing `json` or `dict` export format support
- introducing mutation behavior on the read-only endpoint surface

## Inventory Boundary

The forecasting API remains projection-only.

Inventory remains the source of truth for:

- stock ledger
- stock movement creation
- purchase order creation
- purchase order approval
- operational mutation audit

The forecasting engine remains responsible for:

- advisory projections
- review dashboard response shapes
- export projection response shapes
- validation metadata
- evidence-backed decision review payloads

## Phase 9E Lock

Phase 9E is locked as stability and versioning coverage only.

It does not:

- add new forecasting logic
- mutate inventory
- create stock movements
- create purchase orders
- approve purchase orders
- write export files
- transmit export data
- override ledger truth

## Next Recommended Phase

Phase 9F may focus on OpenAPI/schema documentation or a read-only integration handoff package for desktop/API consumers.

Phase 9F should preserve the same advisory-only and read-only boundary unless a separate approved scope defines otherwise.
