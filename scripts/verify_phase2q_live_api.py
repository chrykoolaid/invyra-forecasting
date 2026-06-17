from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date, timedelta
from urllib.parse import urlparse

LOCAL_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0"}
TIMEOUT_SECONDS = 20


def fail(message: str) -> None:
    print(f"Phase 2Q live API verification failed: {message}", file=sys.stderr)
    raise SystemExit(1)


def info(message: str) -> None:
    print(f"Phase 2Q: {message}")


def api_base_url() -> str:
    raw = os.getenv("INVYRA_FORECASTING_API_BASE_URL", "").strip().rstrip("/")
    if not raw:
        fail("INVYRA_FORECASTING_API_BASE_URL is required.")

    parsed = urlparse(raw)
    if parsed.scheme != "https":
        local_mode = os.getenv("INVYRA_PHASE2Q_ALLOW_HTTP_LOCAL", "").strip().lower() in {"1", "true", "yes"}
        if not (local_mode and parsed.scheme == "http" and parsed.hostname in LOCAL_HOSTS):
            fail("Live hosted verification requires an HTTPS API URL. Use INVYRA_PHASE2Q_ALLOW_HTTP_LOCAL=true only for local smoke tests.")

    return raw


def request_json(method: str, url: str, payload: dict | None = None) -> dict:
    body = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            status = response.status
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        fail(f"{method} {url} returned HTTP {exc.code}: {detail[:500]}")
    except urllib.error.URLError as exc:
        fail(f"{method} {url} failed: {exc.reason}")

    if status < 200 or status >= 300:
        fail(f"{method} {url} returned HTTP {status}")

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        fail(f"{method} {url} did not return valid JSON: {exc}")


def sample_payload() -> dict:
    today = date.today()
    return {
        "actor": "phase2q_live_api_verifier",
        "environment": "LIVE",
        "persist_snapshot": True,
        "forecast_horizon_days": 30,
        "demand_lookback_days": 30,
        "target_cover_days": 14,
        "safety_stock_days": 3,
        "anchor_date": today.isoformat(),
        "item": {
            "id": "PHASE2Q-LIVE-ITEM-001",
            "sku": "CHM-LIVE-002",
            "item_name": "Phase 2Q Live Verification Item",
            "department": "Inventory",
            "uom": "unit",
            "moq": 12,
        },
        "location": {
            "branch_id": "PHASE2Q-BRANCH",
            "branch_name": "Phase 2Q Branch",
            "type": "STORE",
        },
        "stock_position": {
            "item_id": "PHASE2Q-LIVE-ITEM-001",
            "branch_id": "PHASE2Q-BRANCH",
            "stock_on_hand": 18,
            "reserved_stock": 0,
            "environment": "LIVE",
        },
        "movements": [
            {
                "ledger_id": "PHASE2Q-MOV-001",
                "item_id": "PHASE2Q-LIVE-ITEM-001",
                "branch_id": "PHASE2Q-BRANCH",
                "created_at": (today - timedelta(days=2)).isoformat(),
                "source": "POS_SALE",
                "quantity": 3,
                "environment": "LIVE",
            },
            {
                "ledger_id": "PHASE2Q-MOV-002",
                "item_id": "PHASE2Q-LIVE-ITEM-001",
                "branch_id": "PHASE2Q-BRANCH",
                "created_at": (today - timedelta(days=8)).isoformat(),
                "source": "POS_SALE",
                "quantity": 4,
                "environment": "LIVE",
            },
            {
                "ledger_id": "PHASE2Q-MOV-003",
                "item_id": "PHASE2Q-LIVE-ITEM-001",
                "branch_id": "PHASE2Q-BRANCH",
                "created_at": (today - timedelta(days=15)).isoformat(),
                "source": "POS_SALE",
                "quantity": 2,
                "environment": "LIVE",
            },
        ],
        "supplier_profile": {
            "primary_supplier_id": "PHASE2Q-SUPPLIER",
            "item_id": "PHASE2Q-LIVE-ITEM-001",
            "supplier_lead_time_days": 2,
            "lead_time_variability": 1,
            "case_pack": 12,
        },
    }


def assert_guardrails(panel: dict) -> None:
    advisory = panel.get("advisory") or {}
    if advisory.get("advisory_only") is not True:
        fail("forecast panel did not preserve advisory_only=true")
    if advisory.get("inventory_ledger_source_of_truth") is not True:
        fail("forecast panel did not preserve inventory_ledger_source_of_truth=true")
    if advisory.get("mutates_stock") is not False:
        fail("forecast panel must not mutate stock")
    if advisory.get("creates_purchase_order") is not False:
        fail("forecast panel must not create purchase orders")
    if advisory.get("approves_purchase_order") is not False:
        fail("forecast panel must not approve purchase orders")


def main() -> None:
    base = api_base_url()

    health = request_json("GET", f"{base}/health")
    if health.get("status") != "ok":
        fail("/health did not return status=ok")
    if health.get("mode") != "advisory":
        fail("/health did not return mode=advisory")
    info("health endpoint passed")

    panel = request_json("POST", f"{base}/inventory/item-details/forecast", sample_payload())
    status = panel.get("status")
    if status not in {"available", "low_confidence"}:
        fail(f"forecast endpoint returned unexpected status: {status!r}")
    assert_guardrails(panel)
    info(f"forecast endpoint passed with status={status}")

    snapshot_id = panel.get("snapshot_id")
    if snapshot_id:
        evidence = request_json("GET", f"{base}/inventory/item-details/forecast/snapshots/{snapshot_id}")
        if not isinstance(evidence, dict):
            fail("snapshot evidence endpoint did not return an object")
        info(f"snapshot evidence endpoint passed for snapshot_id={snapshot_id}")
    else:
        info("forecast response did not include snapshot_id; snapshot evidence check skipped")

    print("Phase 2Q live API verification passed.")


if __name__ == "__main__":
    main()
