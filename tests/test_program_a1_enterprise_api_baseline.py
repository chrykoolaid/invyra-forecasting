from __future__ import annotations

from fastapi.testclient import TestClient

from invyra_forecasting import __version__
from invyra_forecasting.api.app import app


REQUIRED_GUARDRAILS = (
    "advisory_only",
    "read_only",
    "inventory_source_of_truth_preserved",
)


def _client() -> TestClient:
    return TestClient(app)


def test_root_exposes_enterprise_service_metadata_without_operational_authority() -> None:
    response = _client().get("/")

    assert response.status_code == 200
    payload = response.json()

    assert payload["engine"] == "invyra-forecasting"
    assert payload["engine_version"] == __version__
    assert payload["api_version"] == "v1"
    assert payload["mode"] == "advisory"
    assert "/v1/models" in payload["stable_resources"]

    for guardrail in REQUIRED_GUARDRAILS:
        assert payload[guardrail] is True
    assert payload["no_inventory_mutation"] is True
    assert payload["no_stock_movement_creation"] is True
    assert payload["no_purchase_order_creation"] is True
    assert payload["no_purchase_order_approval"] is True


def test_v1_metadata_includes_enterprise_models_alias() -> None:
    response = _client().get("/v1")

    assert response.status_code == 200
    payload = response.json()

    assert payload["resource"] == "api_metadata"
    assert payload["advisory_only"] is True
    assert payload["read_only"] is True
    assert payload["inventory_source_of_truth_preserved"] is True
    assert "/v1/models" in payload["data"]["stable_resources"]


def test_v1_models_alias_returns_read_only_paginated_model_registry() -> None:
    response = _client().get("/v1/models")

    assert response.status_code == 200
    payload = response.json()

    assert payload["resource"] == "models"
    assert payload["advisory_only"] is True
    assert payload["read_only"] is True
    assert payload["inventory_source_of_truth_preserved"] is True
    assert payload["data"]["count"] >= 1
    assert payload["data"]["pagination"]["total"] >= payload["data"]["count"]
    assert set(payload["data"]["items"][0]) >= {
        "model_id",
        "model_name",
        "model_version",
        "status",
        "metadata",
    }
