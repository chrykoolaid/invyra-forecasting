# Phase 9H — Consumer Compatibility Certification

## Status

Phase 9H certifies that approved downstream consumers can safely integrate with the read-only Forecast Decision Review API surface.

This phase adds compatibility validation coverage and certification documentation only.

## Certified Consumer Surface

The following read-only endpoints are certified for downstream consumption:

```http
GET /forecast/decision-review/dashboard
GET /forecast/decision-review/export
GET /forecast/decision-review/export?export_format=dict
```

The following unsupported request remains intentionally uncertified for successful consumption:

```http
GET /forecast/decision-review/export?export_format=csv
```

It must return HTTP 400 and be treated as a validation issue.

## Certified Reference Client

The reference client certified in this phase is:

```text
src/invyra_forecasting/decision_review_client.py
```

Certified behaviors:

- dashboard projection parsing
- export bundle projection parsing
- JSON export format consumption
- dict export format consumption
- unknown optional field tolerance
- fail-closed governance flag validation
- fail-closed required field type validation
- unsupported export format rejection

## Compatibility Expectations

Certified consumers may rely on:

- stable endpoint paths
- stable successful HTTP status code `200`
- stable unsupported format HTTP status code `400`
- stable governance flags
- stable response version fields
- stable dashboard summary fields
- stable export bundle fields
- additive optional-field compatibility

Certified consumers should not rely on:

- exact key ordering
- fixed `generated_at` values
- absence of optional fields
- undocumented internal queue item details

## Governance Certification

The certified surface remains:

- advisory-only
- read-only
- projection-only
- evidence-backed
- safe for UI/Desktop/API consumers

The certified surface does not:

- mutate inventory
- create stock movements
- create purchase orders
- approve purchase orders
- write export files
- transmit export data
- override ledger truth

Inventory remains the source of truth.

## Certification Tests

Compatibility certification coverage is provided by:

```text
tests/test_phase_9h_consumer_compatibility_certification.py
```

The test suite confirms that the reference client can consume live endpoint shapes and fail closed when compatibility guardrails are violated.

## Consumer Certification Result

Phase 9H certifies the Forecast Decision Review API as ready for controlled read-only integration by approved downstream consumers.

Operational authority remains outside the forecasting engine.
