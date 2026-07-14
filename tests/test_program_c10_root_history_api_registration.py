from __future__ import annotations

from fastapi.testclient import TestClient

from invyra_forecasting.api.app import app


client = TestClient(app)


EXPECTED_HISTORY_ROUTES = {
    "/v1/history",
    "/v1/history/{history_id}",
    "/v1/history/{history_id}/lineage",
    "/v1/history/forecasts/{forecast_id}/versions",
}


def test_root_application_registers_all_history_routes():
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert EXPECTED_HISTORY_ROUTES <= set(paths)


def test_history_routes_expose_no_mutation_methods():
    paths = client.get("/openapi.json").json()["paths"]

    for path in EXPECTED_HISTORY_ROUTES:
        assert set(paths[path]) == {"get"}


def test_root_metadata_advertises_registered_history_resources():
    response = client.get("/")

    assert response.status_code == 200
    resources = set(response.json()["stable_resources"])
    assert EXPECTED_HISTORY_ROUTES <= resources


def test_v1_metadata_advertises_registered_history_resources():
    response = client.get("/v1")

    assert response.status_code == 200
    payload = response.json()
    resources = set(payload["data"]["stable_resources"])
    assert EXPECTED_HISTORY_ROUTES <= resources
    assert payload["advisory_only"] is True
    assert payload["read_only"] is True
    assert payload["inventory_source_of_truth_preserved"] is True
