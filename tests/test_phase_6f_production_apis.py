from __future__ import annotations

from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from invyra_forecasting.api.app import app
from invyra_forecasting.api.production_contracts import ProductionApiEnvelope, paginated_envelope, production_envelope


client = TestClient(app)


def test_phase_6f_metadata_endpoint_uses_stable_v1_envelope() -> None:
    response = client.get("/v1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["api_version"] == "v1"
    assert payload["resource"] == "api_metadata"
    assert payload["advisory_only"] is True
    assert payload["read_only"] is True
    assert payload["inventory_source_of_truth_preserved"] is True
    assert "/v1/forecasts/item" in payload["data"]["stable_resources"]


def test_phase_6f_model_registry_endpoint_is_paginated_and_read_only() -> None:
    response = client.get("/v1/models/registry", params={"limit": 1, "offset": 0})

    assert response.status_code == 200
    payload = response.json()
    assert payload["resource"] == "model_registry"
    assert payload["data"]["count"] == 1
    assert payload["data"]["pagination"]["limit"] == 1
    assert payload["data"]["items"][0]["model_id"] == "baseline_explainable_demand_model::2W.1"
    assert payload["advisory_only"] is True
    assert payload["read_only"] is True


def test_phase_6f_model_capabilities_filters_by_forecast_context() -> None:
    response = client.get(
        "/v1/models/capabilities",
        params={"forecast_type": "item_location_demand", "forecast_days": 30},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["resource"] == "model_capabilities"
    assert payload["metadata"]["forecast_type"] == "item_location_demand"
    assert payload["metadata"]["forecast_days"] == 30
    assert payload["data"]["count"] >= 1


def test_phase_6f_snapshot_endpoint_returns_404_for_missing_snapshot() -> None:
    response = client.get("/v1/snapshots/missing-snapshot")

    assert response.status_code == 404
    assert "Snapshot not found" in response.json()["detail"]


def test_phase_6f_accuracy_endpoint_uses_pagination_envelope_for_empty_results() -> None:
    response = client.get("/v1/evaluations/accuracy/item/item-unknown", params={"limit": 10, "offset": 0})

    assert response.status_code == 200
    payload = response.json()
    assert payload["resource"] == "accuracy_evaluations"
    assert payload["data"]["count"] == 0
    assert payload["data"]["pagination"]["has_more"] is False
    assert payload["advisory_only"] is True
    assert payload["read_only"] is True


def test_phase_6f_production_envelope_rejects_non_read_only_response() -> None:
    envelope = ProductionApiEnvelope(api_version="v1", resource="test", data={})

    with pytest.raises(ValueError, match="production API responses must remain read-only"):
        replace(envelope, read_only=False)


def test_phase_6f_paginated_envelope_rejects_invalid_pagination() -> None:
    with pytest.raises(ValueError, match="limit must be at least 1"):
        paginated_envelope("items", [], limit=0)

    with pytest.raises(ValueError, match="offset must be greater than or equal to 0"):
        paginated_envelope("items", [], limit=1, offset=-1)


def test_phase_6f_production_envelope_returns_guardrail_flags() -> None:
    payload = production_envelope("test", {"ok": True})

    assert payload["api_version"] == "v1"
    assert payload["resource"] == "test"
    assert payload["data"] == {"ok": True}
    assert payload["advisory_only"] is True
    assert payload["read_only"] is True
    assert payload["inventory_source_of_truth_preserved"] is True
