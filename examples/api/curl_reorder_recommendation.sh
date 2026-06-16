#!/usr/bin/env bash
set -euo pipefail

curl -X POST "http://127.0.0.1:8000/recommendations/reorder" \
  -H "Content-Type: application/json" \
  --data-binary @data/sample/api/reorder_recommendation_request.json
