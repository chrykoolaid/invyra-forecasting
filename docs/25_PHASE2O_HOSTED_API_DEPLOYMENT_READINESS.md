# Phase 2O — Hosted Forecasting API Deployment Readiness

Status: IMPLEMENTED / DEPLOYMENT PENDING

## Objective

Prepare the standalone forecasting API for hosted Base44 runtime integration.

The hosted Inventory/Base44 app cannot call a local API. It needs a deployed HTTPS forecasting API URL configured through:

```text
VITE_INVYRA_FORECASTING_API_BASE_URL
```

## API Requirements

The deployed API must expose:

```text
GET /health
POST /inventory/item-details/forecast
GET /inventory/item-details/forecast/snapshots/{snapshot_id}
```

The root route may continue to return 404. The API does not need a homepage route.

## CORS Requirements

The deployed API must allow the hosted Base44 runtime origin.

Configure:

```text
INVYRA_FORECASTING_ALLOWED_ORIGINS=https://app.base44.com
```

If Base44 provides a more specific hosted preview/runtime origin, add that exact origin as well.

## Governance Requirements

Forecasting remains:

```text
advisory only
read-only from Inventory
no stock mutation
no automatic purchase order creation
no automatic purchase order approval
Inventory ledger remains source of truth
safe unavailable state must not break Item Details
```

## Hosted Completion Gate

Hosted runtime can be marked complete only after:

```text
API is reachable over HTTPS
GET /health returns 200
POST /inventory/item-details/forecast returns 200
snapshot endpoint works when snapshot_id exists
Base44 hosted env has the deployed API URL configured
hosted Forecast intelligence panel renders available, low_confidence, or safe unavailable
no stock mutation action appears
no purchase order action appears
```

## Current Result

Phase 2O deployment readiness documentation is in place. Actual hosted runtime verification remains pending until the API is deployed and the Base44 hosted environment is configured.
