# Program E7 — Ranking Evidence Eligibility

Program E7 adds an independent, read-only policy for deciding whether immutable E5 evaluation evidence is trustworthy enough for later adaptive-model-ranking use.

## Eligibility requirements

Evidence is eligible only when it is:

- a final evidence record;
- final-window eligible;
- supported by complete actual-outcome coverage;
- explicitly uncensored by stockouts;
- marked ranking-eligible by the censoring assessment;
- linked to valid model identity and forecast horizon metadata;
- supported by traceable actual-outcome evidence references;
- internally identity-consistent across linkage, outcome, and censoring contracts;
- advisory-only, read-only, and Inventory-source-of-truth preserving.

Ineligible evidence receives explicit exclusion reasons. The policy can filter a collection to eligible records but does not score, rank, weight, aggregate, or feed records into any model selector.

## Compatibility and boundaries

- Existing evaluation persistence remains unchanged.
- Existing E6 APIs remain unchanged.
- Existing evaluation formulas remain unchanged.
- Adaptive model-selection and ranking behaviour remain unchanged.
- No accuracy score, calibration value, bias value, or ranking weight is calculated.
- No automatic data ingestion, retraining, tuning, or operational mutation is introduced.
- Forecasting remains advisory-only and read-only.
- Inventory remains the operational source of truth.
