from fastapi.testclient import TestClient

from invyra_forecasting.api.app import app


client = TestClient(app)
ROUTE = "/v1/intelligence/decisions/review"


def test_decision_review_is_get_only() -> None:
    assert client.post(ROUTE).status_code == 405
    assert client.put(ROUTE).status_code == 405
    assert client.delete(ROUTE).status_code == 405


def test_decision_review_returns_certified_sections(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("INVYRA_FORECAST_HISTORY_DIR", str(tmp_path / "history"))
    monkeypatch.setenv("INVYRA_MODEL_PERFORMANCE_REGISTRY_PATH", str(tmp_path / "registry.jsonl"))
    monkeypatch.setenv("INVYRA_CERTIFIED_STATISTICS_PATH", str(tmp_path / "statistics.jsonl"))

    response = client.get(ROUTE, params={"as_of_utc": "2026-07-31T00:00:00+00:00"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["resource"] == "decision_review"
    data = payload["data"]
    assert set(data) == {"context", "priority", "explanation"}
    assert data["context"]["namespace"] == data["priority"]["namespace"]
    assert data["priority"]["namespace"] == data["explanation"]["namespace"]
    assert data["context"]["as_of_utc"] == "2026-07-31T00:00:00+00:00"
    assert data["context"]["advisory_only"] is True
    assert data["priority"]["read_only"] is True
    assert data["explanation"]["inventory_source_of_truth_preserved"] is True


def test_decision_review_rejects_invalid_timestamp() -> None:
    response = client.get(ROUTE, params={"as_of_utc": "not-a-timestamp"})
    assert response.status_code == 400
