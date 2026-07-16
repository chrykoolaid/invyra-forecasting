# Program G6 — Comparative Portfolio Intelligence

## Purpose

Program G6 compares two tenant-scoped certified enterprise intelligence states using signed, reproducible deltas.

## API

`GET /v1/intelligence/enterprise/compare?baseline_as_of_utc=...&current_as_of_utc=...`

The endpoint reads the latest certified statistics available at each supplied timestamp and reports current-minus-baseline deltas for portfolio coverage, evaluation depth, weighted accuracy, and weighted calibration gap.

## Locked Boundaries

G6 does not declare winners, rank models, select models, recommend action, predict future performance, recalculate certified statistics, or persist comparison results.

The comparison is advisory-only, read-only, tenant-isolated, evidence-backed, and preserves Inventory as the operational source of truth. Existing G1–G5 endpoints and contracts remain unchanged.
