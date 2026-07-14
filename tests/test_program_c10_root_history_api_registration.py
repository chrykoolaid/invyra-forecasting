from __future__ import annotations

from fastapi.testclient import TestClient

from invyra_forecasting.api.app import app


client = TestClient(app)


EXPECTED_HISTORY_ROUTES = {
    "/v1/history": {"GET"},
    "/v1/history/{history_id}": {"GET"},
    "/v1/history/{history_id}/lineage": {"GET"},
    "/v1/history/forecasts/{forecast_id}/versions": {"GET"},
}


def test_root_application_registers_all_history_routes_once():
    registered: dict[str, list[set[str]]] = {}
    for route in app.routes:
        if route.path.startswith("/v1/history"):
            registered.setdefault(route.path, []).append(set(route.methods or ()))

    assert set(registered) == set(EXPECTED_HISTORY_ROUTES)
    for path, expected_methods in EXPECTED_HISTORY_ROUTES.items():
        assert len(registered[path]) == 1
        assert registered[path][0] == expected_methods


def test_history_routes_expose_no_mutation_methods():
    for route in app.routes:
        if route.path.startswith("/v1/history"):
            assert set(route.methods or ()) <= {"GET", "HEAD"}


def test_root_metadata_advertises_registered_history_resources():
    response = client.get("/")

    assert response.status_code == 200
    resources = set(response.json()["stable_resources"])
    assert set(EXPECTED_HISTORY_ROUTES) <= resources


def test_v1_metadata_advertises_registered_history_resources():
    response = client.get("/v1")

    assert response.status_code == 200
    payload = response.json()
    resources = set(payload["data"]["stable_resources"])
    assert set(EXPECTED_HISTORY_ROUTES) <= resources
    assert payload["advisory_only"] is True
    assert payload["read_only"] is True
    assert payload["inventory_source_of_truth_preserved"] is True


def test_registered_history_endpoint_uses_tenant_response_conventions(tmp_path, monkeypatch):
    monkeypatch.setenv("INVYRA_FORECAST_HISTORY_DIR", str(tmp_path / "history"))
    monkeypatch.setenv("INVYRA_FORECAST_EXPLAINABILITY_DIR", str(tmp_path / "explainability"))

    response = client.get("/v1/history", headers={"X-Tenant-Id": " alpha "})

    assert response.status_code == 200
    assert response.headers["X-Tenant-Id"] == "alpha"
    payload = response.json()
    assert payload["resource"] == "forecast_history"
    assert payload["metadata"]["tenant_id"] == "alpha"
    assert payload["data"]["items"] == []
    assert payload["advisory_only"] is True
    assert payload["read_only"] is True
