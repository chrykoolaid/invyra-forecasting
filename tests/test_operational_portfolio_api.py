from fastapi.testclient import TestClient

from invyra_forecasting.api.app import app

client = TestClient(app)


def test_operational_portfolio_route_is_get_only_and_registered() -> None:
    matching = [
        route
        for route in app.routes
        if getattr(route, "path", None) == "/v1/intelligence/operational/portfolio/summary"
    ]
    assert len(matching) == 1
    methods = set(matching[0].methods or ())
    assert "GET" in methods
    assert not (methods & {"POST", "PUT", "PATCH", "DELETE"})


def test_empty_durable_history_returns_honest_read_only_summary(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("INVYRA_FORECAST_HISTORY_DIR", str(tmp_path / "history"))
    response = client.get(
        "/v1/intelligence/operational/portfolio/summary",
        params={"as_of_utc": "2026-07-16T00:00:00+00:00"},
    )
    assert response.status_code == 200
    payload = response.json()
    data = payload["data"]
    assert data["forecast_record_count"] == 0
    assert data["model_usage_distribution"] == {}
    assert data["advisory_only"] is True
    assert data["read_only"] is True
    assert data["inventory_source_of_truth_preserved"] is True


def test_invalid_as_of_timestamp_returns_controlled_bad_request(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("INVYRA_FORECAST_HISTORY_DIR", str(tmp_path / "history"))
    response = client.get(
        "/v1/intelligence/operational/portfolio/summary",
        params={"as_of_utc": "2026-07-16T00:00:00"},
    )
    assert response.status_code == 400
    assert "UTC offset" in response.json()["detail"]
