# Program F7 — Adaptive Decision Explainability

## Purpose

Explain an already completed adaptive model-selection decision by joining the existing Phase 7A audit record to Program F4 governed candidate inputs.

## Explanation content

- selected model and version
- original advisory score and score components
- ranking configuration version
- certified evidence depth and confidence status
- lifecycle, horizon, and demand-profile compatibility
- original rationale and warnings
- alternatives considered
- explicit evaluation evidence references

## Compatibility

F7 preserves the original score order and does not recalculate, reweight, rerank, or reselect candidates. Candidate identity and forecast horizon must match across the audit record and governed input package.

## Boundaries

F7 does not change the Phase 7A selector, model scores, ranking weights, lifecycle state, drift status, forecast generation, APIs, or persistence. Explanations remain advisory-only and read-only, and Inventory remains the operational source of truth.
