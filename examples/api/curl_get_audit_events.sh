#!/usr/bin/env bash
set -euo pipefail

curl "http://127.0.0.1:8000/audit/events?limit=25"
