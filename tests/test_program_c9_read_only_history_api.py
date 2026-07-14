from __future__ import annotations

from contextlib import contextmanager

from fastapi import FastAPI
from fastapi.testclient import TestClient

from invyra_forecasting.api import tenant_context
from invyra_forecasting.api.history_routes import router
from invyra_forecasting.api.tenant_context import TenantContextMiddleware
from invyra_forecasting.history import ForecastHistoryRecord
from invyra_forecasting.history_persistence import FileForecastHistoryRepository


@contextmanager
def _tenant(tenant_id: str | None):
    token = tenant_context._TENANT_ID.set(tenant_context.normalize_tenant_id(tenant_id))
    try:
        yield
    finally:
        tenant_context._TENANT_ID.reset(token)


def _record(
    history_id: str,
    *,
    forecast_id: str = "forecast-1",
    version_number: int = 1,
    parent_history_id: str | None = None,
    snapshot_id: str = "snapshot-1",
    created_at_utc: str = "2026-07-14T10:00:00+00:00",
) -> ForecastHistoryRecord:
    return ForecastHistoryRecord(
        history_id=history_id,
        forecast_id=forecast_id,
        item_id="ITEM-001",
        location_id="LOC-001",
        model_name="seasonal-naive",
        model_version="1.0",
        forecast_payload={"forecast_quantity": 12.0},
        version_number=version_number,
        parent_history_id=parent_history_id,
        snapshot_id=snapshot_id,
        created_at_utc=created_at_utc,
    )


def _client() -> TestClient:
    app = FastAPI()
    app.add_middleware(TenantContextMiddleware)
    app.include_router(router)
    return TestClient(app)


def _configure(monkeypatch, tmp_path):
    history_dir = tmp_path / "history"
    explainability_dir = tmp_path / "explainability"
    monkeypatch.setenv("INVYRA_FORECAST_HISTORY_DIR", str(history_dir))
    monkeypatch.setenv("INVYRA_FORECAST_EXPLAINABILITY_DIR", str(explainability_dir))
    return FileForecastHistoryRepository(history_dir)


def test_get_history_record_uses_stable_read_only_envelope(monkeypatch, tmp_path):
    repository = _configure(monkeypatch, tmp_path)
    repository.append(_record("history-1"))

    response = _client().get("/v1/history/history-1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["resource"] == "forecast_history_record"
    assert payload["data"]["history"]["history_id"] == "history-1"
    assert payload["data"]["explainability"] is None
    assert payload["advisory_only"] is True
    assert payload["read_only"] is True
    assert payload["inventory_source_of_truth_preserved"] is True


def test_missing_history_record_returns_404(monkeypatch, tmp_path):
    _configure(monkeypatch, tmp_path)

    response = _client().get("/v1/history/missing")

    assert response.status_code == 404
    assert response.json()["detail"] == "History record not found: missing"


def test_list_history_supports_filters_and_pagination(monkeypatch, tmp_path):
    repository = _configure(monkeypatch, tmp_path)
    repository.append(_record("history-1", snapshot_id="snapshot-a"))
    repository.append(
        _record(
            "history-2",
            forecast_id="forecast-2",
            snapshot_id="snapshot-b",
            created_at_utc="2026-07-14T11:00:00+00:00",
        )
    )
    repository.append(
        _record(
            "history-3",
            forecast_id="forecast-3",
            snapshot_id="snapshot-b",
            created_at_utc="2026-07-14T12:00:00+00:00",
        )
    )

    response = _client().get(
        "/v1/history",
        params={"snapshot_id": "snapshot-b", "limit": 1, "offset": 1},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["pagination"] == {"limit": 1, "offset": 1, "total": 2}
    assert data["items"][0]["history"]["history_id"] == "history-3"


def test_versions_and_lineage_are_restart_safe(monkeypatch, tmp_path):
    repository = _configure(monkeypatch, tmp_path)
    first = _record("history-v1")
    second = _record(
        "history-v2",
        version_number=2,
        parent_history_id="history-v1",
        created_at_utc="2026-07-14T11:00:00+00:00",
    )
    repository.append(first)
    repository.append(second)
    client = _client()

    versions = client.get("/v1/history/forecasts/forecast-1/versions")
    lineage = client.get("/v1/history/history-v2/lineage")

    expected = ["history-v1", "history-v2"]
    assert versions.status_code == 200
    assert [item["history"]["history_id"] for item in versions.json()["data"]["items"]] == expected
    assert lineage.status_code == 200
    assert [item["history"]["history_id"] for item in lineage.json()["data"]["items"]] == expected


def test_history_routes_are_tenant_isolated(monkeypatch, tmp_path):
    repository = _configure(monkeypatch, tmp_path)

    with _tenant("alpha"):
        repository.append(_record("shared-id", forecast_id="forecast-alpha"))
    with _tenant("bravo"):
        repository.append(_record("shared-id", forecast_id="forecast-bravo"))

    client = _client()
    alpha = client.get("/v1/history/shared-id", headers={"X-Tenant-Id": "alpha"})
    bravo = client.get("/v1/history/shared-id", headers={"X-Tenant-Id": "bravo"})

    assert alpha.json()["data"]["history"]["forecast_id"] == "forecast-alpha"
    assert alpha.json()["metadata"]["tenant_id"] == "alpha"
    assert bravo.json()["data"]["history"]["forecast_id"] == "forecast-bravo"
    assert bravo.json()["metadata"]["tenant_id"] == "bravo"


def test_invalid_query_returns_400(monkeypatch, tmp_path):
    _configure(monkeypatch, tmp_path)

    response = _client().get("/v1/history", params={"version_number": 0})

    assert response.status_code == 400
    assert response.json()["detail"] == "version_number must be greater than or equal to 1"
