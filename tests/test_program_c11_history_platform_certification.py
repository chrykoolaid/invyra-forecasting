from __future__ import annotations

from contextlib import contextmanager

from fastapi.testclient import TestClient

from invyra_forecasting.api import tenant_context
from invyra_forecasting.api.app import app
from invyra_forecasting.explainability_archive import HistoricalExplainabilityRecord
from invyra_forecasting.explainability_persistence import FileHistoricalExplainabilityRepository
from invyra_forecasting.history import ForecastHistoryRecord
from invyra_forecasting.history_persistence import FileForecastHistoryRepository


client = TestClient(app)


@contextmanager
def _tenant(tenant_id: str | None):
    token = tenant_context._TENANT_ID.set(tenant_context.normalize_tenant_id(tenant_id))
    try:
        yield
    finally:
        tenant_context._TENANT_ID.reset(token)


def _history(
    history_id: str,
    *,
    forecast_id: str,
    quantity: float,
    version_number: int = 1,
    parent_history_id: str | None = None,
) -> ForecastHistoryRecord:
    return ForecastHistoryRecord(
        history_id=history_id,
        forecast_id=forecast_id,
        item_id="ITEM-001",
        location_id="LOC-001",
        model_name="seasonal-naive",
        model_version="1.0",
        forecast_payload={"forecast_quantity": quantity},
        version_number=version_number,
        parent_history_id=parent_history_id,
        snapshot_id=f"snapshot-{history_id}",
        evidence_refs=(f"evidence-{history_id}",),
    )


def _explainability(
    archive_id: str,
    *,
    history_id: str,
    forecast_id: str,
    confidence: float,
) -> HistoricalExplainabilityRecord:
    return HistoricalExplainabilityRecord(
        archive_id=archive_id,
        history_id=history_id,
        forecast_id=forecast_id,
        model_name="seasonal-naive",
        model_version="1.0",
        confidence=confidence,
        explanation=("Certified historical explanation.",),
        evidence_refs=(f"evidence-{history_id}",),
    )


def _configure_storage(tmp_path, monkeypatch):
    history_dir = tmp_path / "history"
    explainability_dir = tmp_path / "explainability"
    monkeypatch.setenv("INVYRA_FORECAST_HISTORY_DIR", str(history_dir))
    monkeypatch.setenv("INVYRA_FORECAST_EXPLAINABILITY_DIR", str(explainability_dir))
    return (
        FileForecastHistoryRepository(history_dir),
        FileHistoricalExplainabilityRepository(explainability_dir),
    )


def test_durable_api_reads_are_tenant_isolated_end_to_end(tmp_path, monkeypatch):
    history_store, explainability_store = _configure_storage(tmp_path, monkeypatch)

    with _tenant("alpha"):
        history_store.append(_history("shared-history", forecast_id="forecast-alpha", quantity=10.0))
        explainability_store.append(
            _explainability(
                "shared-archive",
                history_id="shared-history",
                forecast_id="forecast-alpha",
                confidence=0.9,
            )
        )

    with _tenant("bravo"):
        history_store.append(_history("shared-history", forecast_id="forecast-bravo", quantity=20.0))
        explainability_store.append(
            _explainability(
                "shared-archive",
                history_id="shared-history",
                forecast_id="forecast-bravo",
                confidence=0.4,
            )
        )

    alpha = client.get("/v1/history/shared-history", headers={"X-Tenant-Id": "alpha"})
    bravo = client.get("/v1/history/shared-history", headers={"X-Tenant-Id": "bravo"})

    assert alpha.status_code == 200
    assert bravo.status_code == 200
    assert alpha.json()["data"]["history"]["forecast_id"] == "forecast-alpha"
    assert alpha.json()["data"]["explainability"]["confidence"] == 0.9
    assert bravo.json()["data"]["history"]["forecast_id"] == "forecast-bravo"
    assert bravo.json()["data"]["explainability"]["confidence"] == 0.4


def test_durable_version_and_lineage_endpoints_survive_provider_rebuild(tmp_path, monkeypatch):
    history_store, _ = _configure_storage(tmp_path, monkeypatch)

    first = _history("history-v1", forecast_id="forecast-1", quantity=10.0)
    second = _history(
        "history-v2",
        forecast_id="forecast-1",
        quantity=12.0,
        version_number=2,
        parent_history_id="history-v1",
    )
    history_store.append(first)
    history_store.append(second)

    versions = client.get("/v1/history/forecasts/forecast-1/versions")
    lineage = client.get("/v1/history/history-v2/lineage")

    assert versions.status_code == 200
    assert lineage.status_code == 200
    assert [item["history"]["history_id"] for item in versions.json()["data"]["items"]] == [
        "history-v1",
        "history-v2",
    ]
    assert [item["history"]["history_id"] for item in lineage.json()["data"]["items"]] == [
        "history-v1",
        "history-v2",
    ]


def test_history_api_surface_is_read_only_and_stable():
    schema = client.get("/openapi.json").json()
    history_paths = {
        path: operations
        for path, operations in schema["paths"].items()
        if path.startswith("/v1/history")
    }

    assert set(history_paths) == {
        "/v1/history",
        "/v1/history/{history_id}",
        "/v1/history/{history_id}/lineage",
        "/v1/history/forecasts/{forecast_id}/versions",
    }
    assert all(set(operations) == {"get"} for operations in history_paths.values())


def test_history_api_preserves_enterprise_guardrails(tmp_path, monkeypatch):
    _configure_storage(tmp_path, monkeypatch)

    payload = client.get("/v1/history").json()

    assert payload["advisory_only"] is True
    assert payload["read_only"] is True
    assert payload["inventory_source_of_truth_preserved"] is True
    assert payload["data"]["advisory_only"] is True
    assert payload["data"]["read_only"] is True
    assert payload["data"]["inventory_source_of_truth_preserved"] is True
