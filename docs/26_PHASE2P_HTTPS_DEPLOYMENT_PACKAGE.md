# Phase 2P — Forecasting API HTTPS Deployment Package

Status: IMPLEMENTED / DEPLOYMENT TARGET PENDING

## Objective

Package the standalone Invyra Forecasting API for deployment to an HTTPS host so hosted Base44 can call it through `VITE_INVYRA_FORECASTING_API_BASE_URL`.

This phase does not change the API contract or forecasting behavior.

## Deployment Files Added

```text
Dockerfile
.dockerignore
.env.production.example
scripts/validate_phase2p_deployment_readiness.py
```

## Runtime Entrypoint

The production container starts:

```text
uvicorn invyra_forecasting.api.app:app --host 0.0.0.0 --port ${PORT:-8000}
```

Many hosts inject `PORT` automatically. If not, set:

```text
INVYRA_FORECASTING_PORT=8000
```

## Required Production Environment

Set exact hosted origins. Do not use wildcard CORS.

```text
INVYRA_FORECASTING_ALLOWED_ORIGINS=https://app.base44.com
```

If Base44 provides a more specific hosted preview/runtime origin, add it as a comma-separated value.

Optional storage paths:

```text
INVYRA_FORECASTING_SNAPSHOT_DIR=./data/snapshots
INVYRA_FORECASTING_AUDIT_LOG_PATH=./data/audit/events.jsonl
INVYRA_FORECASTING_ACCURACY_LOG_PATH=./data/accuracy/accuracy.jsonl
INVYRA_FORECASTING_REPORT_EXPORT_DIR=./data/reports
```

Use durable mounted storage for these paths if the deployment platform supports volumes.

## Local Container Smoke Test

Build:

```bash
docker build -t invyra-forecasting-api .
```

Run:

```bash
docker run --rm -p 8000:8000 -e INVYRA_FORECASTING_ALLOWED_ORIGINS=https://app.base44.com invyra-forecasting-api
```

Check:

```bash
curl http://127.0.0.1:8000/health
```

Expected:

```text
status: ok
mode: advisory
```

## Deployment Readiness Validation

Run:

```bash
INVYRA_FORECASTING_ALLOWED_ORIGINS=https://app.base44.com python scripts/validate_phase2p_deployment_readiness.py
```

Expected:

```text
Phase 2P deployment readiness validation passed.
```

This validation is now included in CI.

## API Routes Required By Hosted Base44

```text
GET /health
POST /inventory/item-details/forecast
GET /inventory/item-details/forecast/snapshots/{snapshot_id}
```

The root route may continue returning 404. The API does not need a homepage route.

## Hosted Completion Gate

Phase 2P can be marked deployment-passing only when:

```text
API is deployed to HTTPS
GET /health returns 200 over HTTPS
POST /inventory/item-details/forecast returns 200 over HTTPS
CORS allows the hosted Base44 origin
snapshot endpoint works when snapshot_id exists
hosted Base44 can be configured with the HTTPS API URL
```

## Governance Lock

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
