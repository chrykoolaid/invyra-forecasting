# Program F1 — Model Performance Registry Foundation

Program F1 establishes a governed, immutable catalog of forecasting model metadata and versions.

Each registry entry records:

- model name and version;
- lifecycle status;
- supported forecast horizons;
- supported demand profiles;
- tenant namespace;
- registration timestamp and schema version;
- advisory-only, read-only, and Inventory source-of-truth guardrails.

## Lifecycle States

- `experimental`
- `active`
- `observation`
- `deprecated`
- `retired`

These states are descriptive metadata in F1. They do not change selection behaviour.

## Storage and Compatibility

The registry is append-only and rejects duplicate registry IDs and duplicate model/version pairs within the same tenant namespace. Separate model versions remain preserved as independent immutable entries.

F1 provides both in-memory and local JSONL repositories. Durable records reconstruct after restart while retaining tenant isolation. The default architecture remains local/server-first and introduces no database or cloud dependency.

## Explicit Boundaries

F1 does not calculate accuracy, bias, calibration, confidence, ranking scores, ranks, or weights. It does not call or modify the adaptive selector, retire models automatically, retrain models, tune parameters, change forecast generation, or alter Program E evidence.

No API route or operational mutation is introduced. Forecasting remains advisory-only and read-only. Inventory remains the operational source of truth. No inventory, stock movement, sales, transfer, wastage, markdown, or purchase-order mutation is permitted.
