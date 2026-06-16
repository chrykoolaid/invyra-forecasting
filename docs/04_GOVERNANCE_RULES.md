# Governance Rules

1. Forecasting is advisory, not the source of truth.
2. Inventory ledger remains the source of truth.
3. Forecasts must include confidence.
4. Forecast recommendations must include explanations.
5. Manager override must be audit-logged.
6. Forecasting must support item + location level calculations.
7. Forecasting must support LIVE / TRAINING / TEST separation.
8. No auto-purchasing in v1.
9. No fake AI claims in v1.
10. Start with simple, explainable forecasting before advanced ML.
11. Low-confidence forecasts must be shown honestly.
12. Forecasting must not hide missing or poor inventory data.
13. Forecasting must not bypass existing Inventory, ScanOps, Purchasing, or Stock Movement logic.
14. Forecasting must preserve auditability and traceability.
15. Forecast outputs must be reproducible from saved input snapshots where possible.

## Override Governance

A manager may override a recommendation, but the override must create an audit event containing actor, timestamp, environment, item/location, original recommendation, override action, and reason.

## Environment Separation

Every forecast input and output must carry `LIVE`, `TRAINING`, or `TEST`. The engine must not combine records across environments.
