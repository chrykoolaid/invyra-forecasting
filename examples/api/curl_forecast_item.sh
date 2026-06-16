#!/usr/bin/env bash
set -euo pipefail

curl -X POST "http://127.0.0.1:8000/forecasts/item" \
  -H "Content-Type: application/json" \
  --data-binary @data/sample/api/forecast_item_request.json
