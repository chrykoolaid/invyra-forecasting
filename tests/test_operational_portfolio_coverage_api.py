from fastapi.testclient import TestClient

from invyra_forecasting.api.app import app
from invyra_forecasting.api.operational_portfolio_routes import router
from invyra_forecasting.history import ForecastHistoryRecord
from invyra_forecasting.history_persistence import FileForecastHistoryRepository

client = TestClient(app)


def _record(
    history_id: str,
    *,
    evidence: bool,
    snapshot: bool,
    created_at_utc: str,
) -> ForecastHistoryRecord:
    return ForecastHistoryRecord(
        history_id=history_id,
        forecast_id=f"forecast-{history_id}",
        item_id="ITEM-1",
        location_id="LOC-1",
        model_name="seasonal-naive",
        model_version="1.0",
        forecast_payload={"forecast_quantity": 10.0},
        created_at_utc=created_at_utc,
        snapshot_id=f"snapshot-{history_id}" if snapshot else None,
        evidence_refs=(f"evidence-{history_id}",) if evidence else (),
    )


def test_coverage_route_is_get_only() -> None:
    matching = [
        route
        for route in router.routes
        if route.path == "/v1/intelligence/operational/portfolio/coverage"
    ]
    assert len(matching) == 1
    methods = set(matching[0].methods or ())
    assert "GET" in methods
    assert not methods.intersection({"POST", "PUT", "PATCH", "DELETE"})


def test_coverage_endpoint_reads_durable_history(tmp_path, monkeypatch) -> None:
    history_dir = tmp_path / "history"
    monkeypatch.setenv("INVYRA_FORECAST_HISTORY_DIR", str(history_dir))
    repository = FileForecastHistoryRepository(history_dir)
    repository.append(
        _record(
            "h1",
            evidence=True,
            snapshot=True,
            created_at_utc="2026-07-01T00:00:00+00:00",
        )
    )
    repository.append(
        _record(
            "h2",
            evidence=True,
            snapshot=False,
            created_at_utc="2026-07-02T00:00:00+00:00",
        )
    )

    response = client.get(
        "/v1/intelligence/operational/portfolio/coverage",
        params={"as_of_utc": "2026-07-10T00:00:00+00:00"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["resource"] == "operational_forecast_portfolio_coverage"
    assert payload["advisory_only"] is True
    assert payload["read_only"] is True
    data = payload["data"]
    assert data["status"] == "developing"
    assert data["forecast_record_count"] == 2
    assert data["evidence_coverage_ratio"] == 1.0
    assert data["snapshot_coverage_ratio"] == 0.5
    assert data["advisory_only"] is True
    assert data["inventory_source_of_truth_preserved"] is True
    assert data["history_refs"] == ["h1", "h2"]


def test_coverage_endpoint_returns_honest_empty_state(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("INVYRA_FORECAST_HISTORY_DIR", str(tmp_path / "history"))
    response = client.get(
        "/v1/intelligence/operational/portfolio/coverage",
        params={"as_of_utc": "2026-07-10T00:00:00+00:00"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "unavailable"
    assert data["forecast_record_count"] == 0
    assert data["evidence_coverage_ratio"] is None
    assert data["snapshot_coverage_ratio"] is None


def test_coverage_endpoint_returns_controlled_bad_request(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("INVYRA_FORECAST_HISTORY_DIR", str(tmp_path / "history"))
    response = client.get(
        "/v1/intelligence/operational/portfolio/coverage",
        params={"as_of_utc": "2026-07-10T00:00:00"},
    )
    assert response.status_code == 400
    assert "UTC offset" in response.json()["detail"]
