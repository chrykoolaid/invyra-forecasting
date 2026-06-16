# Integration Fixtures — Phase 1C

Phase 1C adds stable request examples for modules that will call the forecasting engine.

The fixtures are not production data. They are integration contracts and safe examples for developers.

## Shared API Fixtures

Shared fixtures live in:

```text
data/sample/api/
```

Files:

- `forecast_item_request.json`
- `batch_forecast_request.json`
- `stockout_risk_request.json`
- `reorder_recommendation_request.json`
- `override_audit_request.json`

## Module Fixtures

Module-specific fixtures live in:

```text
integrations/<module>/fixtures/
```

Current modules:

- Inventory
- ScanOps
- Reorder Review
- Purchasing
- Dashboard
- Reports
- Suppliers
- Markdowns
- Wastage
- POS
- CRM

## Integration Rules

1. Fixtures are advisory examples, not source-of-truth data.
2. All payloads must include `environment`.
3. Forecasting endpoints must not mutate inventory stock.
4. Reorder recommendation fixtures must not create purchase orders.
5. Override audit fixtures must only create audit records.
6. Low-confidence data should remain visible and must not be hidden by integrations.

## Local API Test

Start the API:

```bash
uvicorn invyra_forecasting.api.app:app --reload
```

Then call an example:

```bash
curl -X POST http://127.0.0.1:8000/forecasts/item \
  -H "Content-Type: application/json" \
  --data-binary @data/sample/api/forecast_item_request.json
```

Windows PowerShell:

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/forecasts/item" -ContentType "application/json" -InFile "data/sample/api/forecast_item_request.json"
```
