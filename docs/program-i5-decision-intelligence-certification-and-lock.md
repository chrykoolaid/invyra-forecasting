# Program I5 — Decision Intelligence Governance and Certification Lock

## Status

Program I1 through I4 are certified as a governed, read-only decision-review capability.

## Certified scope

- I1 Decision Context composes existing certified enterprise and operational intelligence.
- I2 Decision Priority applies fixed deterministic precedence without numeric scoring.
- I3 Decision Explainability renders the certified priority and reasons without changing policy.
- I4 Decision Review API exposes one tenant-isolated GET endpoint at a reproducible `as_of_utc` boundary.

## Permanent governance boundaries

Decision Intelligence remains:

- advisory-only
- read-only
- deterministic
- evidence-backed
- tenant-isolated
- reproducible by timestamp
- subordinate to Inventory as the operational source of truth

It must not:

- recalculate forecasts or certified metrics
- score or rank items, locations, models, suppliers, or tenants
- recommend or select an operational action
- predict an inventory outcome
- infer live inventory truth
- mutate inventory or stock
- create stock movements
- create or approve purchase orders
- mutate forecast history or evidence
- autonomously execute any workflow

## Contract lock

The top-level Program I contracts remain immutable dataclasses and retain:

- `namespace`
- `as_of_utc`
- `evidence_refs`
- `history_refs`
- `advisory_only`
- `read_only`
- `inventory_source_of_truth_preserved`

## Service-surface lock

The public service surfaces are limited to:

- `DecisionContextService.compose`
- `DecisionPriorityPolicy.assess`
- `DecisionExplanationService.explain`

No ranking, recommendation, prediction, selection, execution, or mutation method is permitted.

## API lock

The certified Decision Intelligence API surface is:

- `GET /v1/intelligence/decisions/review`

No Decision Intelligence POST, PUT, PATCH, or DELETE route is certified or permitted by this program.

## Change control

Future changes to Program I require a new governed program increment, focused regression tests, a pull request, and green CI before merge. Program I5 itself changes no production runtime behavior.
