#!/usr/bin/env bash
set -euo pipefail

curl -X POST "http://127.0.0.1:8000/risk/stockout" \
  -H "Content-Type: application/json" \
  --data-binary @data/sample/api/stockout_risk_request.json
