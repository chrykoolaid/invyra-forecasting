#!/usr/bin/env bash
set -euo pipefail

curl -X POST "http://127.0.0.1:8000/accuracy/evaluate" \
  -H "Content-Type: application/json" \
  --data-binary @data/sample/api/accuracy_evaluate_request.json
