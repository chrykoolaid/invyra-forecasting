# Phase 2Q.1 — Render Deployment Preparation

Status: IMPLEMENTED / USER DEPLOYMENT ACTION REQUIRED

## Objective

Prepare the forecasting API repo for a Docker-based hosted deployment target.

## Added File

```text
render.yaml
```

## Blueprint Summary

The blueprint defines a Docker web service with:

```text
service name: invyra-forecasting-api
health check: /health
persistent data mount: /var/data
CORS origin: https://app.base44.com
```

Forecasting remains advisory only. This deployment file does not add stock mutation, purchase order creation, or purchase order approval.

## Render Deployment Steps

1. Open Render.
2. Create a new Blueprint or web service from the GitHub repo.
3. Select `chrykoolaid/invyra-forecasting`.
4. Use the root `render.yaml` blueprint if prompted.
5. Confirm the environment variable:

```text
INVYRA_FORECASTING_ALLOWED_ORIGINS=https://app.base44.com
```

6. Deploy.
7. Copy the HTTPS service URL after deployment.

## Verify The Live URL

Set:

```text
INVYRA_FORECASTING_API_BASE_URL=https://your-render-service-url
```

Run:

```text
python scripts/verify_phase2q_live_api.py
```

Expected:

```text
Phase 2Q live API verification passed.
```

## Hosted Base44 Follow-Up

After live verification passes, configure hosted Base44 with:

```text
VITE_INVYRA_FORECASTING_API_BASE_URL=https://your-render-service-url
```

Then test hosted Item Details forecast intelligence.

## Completion Gate

Phase 2Q can be marked live-passing only after the deployed HTTPS URL passes the live verifier.
