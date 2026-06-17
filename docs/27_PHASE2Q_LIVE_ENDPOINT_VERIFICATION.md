# Phase 2Q — Live Endpoint Verification

Status: IMPLEMENTED / LIVE URL PENDING

## Objective

Verify a deployed HTTPS Forecasting API endpoint before connecting hosted Base44.

## Added File

```text
scripts/verify_phase2q_live_api.py
```

## Required Environment

```text
INVYRA_FORECASTING_API_BASE_URL=https://deployed-forecasting-api-host
```

## Verification Scope

The verifier checks:

```text
health endpoint returns status ok
health endpoint returns advisory mode
item details forecast endpoint returns available or low_confidence
advisory-only guardrail remains true
ledger source-of-truth guardrail remains true
stock mutation remains false
purchase order creation remains false
purchase order approval remains false
snapshot evidence endpoint works when snapshot_id exists
```

## Run

```text
Set INVYRA_FORECASTING_API_BASE_URL to the deployed HTTPS API URL.
Run python scripts/verify_phase2q_live_api.py.
```

Expected result:

```text
Phase 2Q live API verification passed.
```

## Local Smoke Mode

Local HTTP testing is allowed only when:

```text
INVYRA_PHASE2Q_ALLOW_HTTP_LOCAL=true
```

This is not valid for hosted completion.

## Completion Gate

Phase 2Q can be marked live-passing only after:

```text
API is deployed to HTTPS
live verifier passes against the HTTPS URL
hosted Base44 can use the same HTTPS URL
hosted Forecast intelligence remains advisory only
no stock adjustment action appears
no purchase order action appears
```

## Current Result

Verification tooling is complete. Live endpoint verification is pending until a deployed HTTPS API URL exists.
