# Phase 2K — Forecasting API Runtime Connectivity Hardening

Status: implemented foundation

## Objective

Phase 2K prepares the forecasting API for browser calls from the Inventory/Base44 Item Details forecast panel.

This phase does not change forecasting behaviour. It only adds runtime connectivity settings required before testing the API-configured Base44 path.

## Added Runtime Settings

New file:

```text
src/invyra_forecasting/api/runtime.py
```

The runtime module defines:

- default allowed browser origins
- allowed HTTP methods
- allowed headers
- origin parser
- origin checker

## CORS Middleware

The FastAPI app now adds CORS middleware using explicit environment-based origins.

Default allowed origins:

```text
http://localhost:5173
http://127.0.0.1:5173
https://app.base44.com
```

Allowed methods:

```text
GET
POST
OPTIONS
```

Allowed headers:

```text
Content-Type
```

Wildcard origins are not accepted. Use explicit origins only.

## Forecasting API Environment Variable

Set this on the forecasting API runtime host:

```text
INVYRA_FORECASTING_ALLOWED_ORIGINS=https://app.base44.com,http://localhost:5173,http://127.0.0.1:5173
```

When a production Inventory URL exists later, add that exact URL to the comma-separated list.

## Inventory/Base44 Environment Variable

Set this in the Inventory/Base44 app when the forecasting API is available:

```text
VITE_INVYRA_FORECASTING_API_BASE_URL=<forecasting-api-url>
```

Local example:

```text
VITE_INVYRA_FORECASTING_API_BASE_URL=http://127.0.0.1:8000
```

The Inventory panel already fails closed when this value is blank or unreachable.

## Local Runtime Smoke Test

Forecasting repo:

```text
pip install -e ".[api,dev]"
set INVYRA_FORECASTING_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,https://app.base44.com
uvicorn invyra_forecasting.api.app:app --reload
```

Inventory/Base44 repo or Base44 environment:

```text
VITE_INVYRA_FORECASTING_API_BASE_URL=http://127.0.0.1:8000
```

Then open:

```text
Inventory -> View item -> Item Details
```

Expected result:

- Forecast panel calls `POST /inventory/item-details/forecast`.
- Panel shows `available`, `low_confidence`, or safe `unavailable`.
- Low-confidence forecasts remain visible.
- Snapshot evidence link appears only when a snapshot ID exists.
- Item Details remains usable if the API returns unavailable.

## Tests

Added tests:

```text
tests/test_phase2k_api_runtime_connectivity.py
```

Coverage includes:

- default local/Base44 origins
- explicit origin parsing
- trailing slash normalization
- wildcard origin rejection
- allowed origin checking
- limited methods and headers

## Guardrails Preserved

Phase 2K does not:

- mutate stock
- create purchase orders
- approve purchase orders
- change forecast models
- change Item Details UI
- change Inventory ledger truth

## Phase 2K Exit Status

Phase 2K prepares the API for the remaining API-configured Base44 runtime test.

Next recommended phase:

```text
Phase 2L — API-configured Base44 runtime verification
```
