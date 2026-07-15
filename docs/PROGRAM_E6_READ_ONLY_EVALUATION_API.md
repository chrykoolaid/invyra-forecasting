# Program E6 — Read-Only Evaluation API

Program E6 exposes tenant-scoped read models over the immutable E5 evaluation-evidence store.

## Stable resources

- `GET /v1/evaluations`
- `GET /v1/evaluations/{evaluation_id}`
- `GET /v1/history/{history_id}/evaluation`
- `GET /v1/models/{model_name}/performance`

The list resource supports evaluation, history, forecast, item, location, model, model-version, and evidence-stage filters with bounded pagination.

The model-performance resource reports evidence counts, final-readiness, ranking-eligible evidence, and censoring classifications. It does not calculate new accuracy metrics or change adaptive model ranking.

## Compatibility

The pre-E6 FastAPI implementation is preserved unchanged in `api/legacy_app.py`. The public `api/app.py` remains the compatibility entrypoint, re-exports the existing app surface, and registers the E6 router.

## Guardrails

- Read-only GET routes only.
- Tenant-isolated reconstruction and queries.
- Existing accuracy API remains unchanged.
- Existing evaluation formulas remain unchanged.
- No evaluation creation or mutation endpoint.
- No operational-data ingestion.
- No inventory, stock movement, sales, transfer, wastage, markdown, or purchase-order mutation.
- Inventory remains the operational source of truth.
