# Program E8 — Evaluation Platform Certification and Lock

## Certified scope

Program E8 certifies the Program E outcome-evaluation platform delivered through E1–E7.

The certification covers:

- immutable linkage between forecast history and evaluation identity;
- evaluation-window governance;
- normalized actual-outcome evidence;
- stockout-censoring classification without demand reconstruction;
- append-only partial-to-final evidence persistence;
- tenant-isolated restart reconstruction;
- read-only evaluation APIs;
- request-correlation metadata;
- versioned ranking-evidence eligibility decisions;
- preservation of observed quantities and Inventory source-of-truth governance.

## Certified guarantees

1. Partial evidence may be preserved before final readiness.
2. Final evidence is separately identifiable and restart-safe.
3. Only final, complete, uncensored, identity-valid evidence qualifies for later ranking use.
4. Eligibility decisions do not calculate scores, ranks, weights, calibration, bias, or new accuracy metrics.
5. Evaluation APIs expose GET operations only.
6. Tenant namespaces remain isolated through persistence reconstruction and API reads.
7. Request IDs remain available in stable API metadata and response headers.
8. Inventory remains the operational source of truth.
9. The forecasting engine remains advisory-only and read-only.

## Program E slices

- E1 — Forecast Evaluation Linkage Foundation
- E2 — Evaluation Window Governance
- E3 — Actual Outcome Input Contract
- E4 — Stockout Censoring Classification
- E5 — Evaluation Persistence Integration
- E6 — Read-Only Evaluation API
- E7 — Ranking Evidence Eligibility
- E8 — Evaluation Platform Certification and Lock

## Explicit non-goals

Program E does not introduce automatic operational-data ingestion, lost-sales estimation, missing-demand reconstruction, model retraining, automatic tuning, selector integration, ranking-score changes, inventory mutation, stock movement creation, purchase-order creation or approval, cloud replication, or a distributed evaluation backend.

## Lock rule

Program E is complete when the E8 certification tests and the full GitHub CI workflow pass and the certification PR is merged.

Further evaluation or adaptive-ranking integration requires a new, separately approved program or a concrete evidence-backed defect. No additional Program E runtime expansion is permitted by default.
