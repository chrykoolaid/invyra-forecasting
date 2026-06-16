#!/usr/bin/env bash
set -euo pipefail

curl "http://127.0.0.1:8000/accuracy/item/ITEM-001?environment=TRAINING&limit=25"
