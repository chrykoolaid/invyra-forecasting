# Program I3 — Decision Explainability

Program I3 adds a deterministic explanation of the certified Program I1 Decision Context and Program I2 Decision Priority.

Delivered:
- immutable DecisionExplanation contract
- fixed headline and summary from the certified priority
- explicit reason codes and reasons
- preserved evidence and history references
- tenant, timestamp, reference, and governance validation
- defensive serialization

Boundaries:
- no forecast or metric recalculation
- no priority-policy change
- no scoring, ranking, recommendation, prediction, or automated action
- no Inventory, order, history, or evidence mutation
- no persistence or public API

Forecasting remains advisory-only and read-only. Inventory remains the operational source of truth.
