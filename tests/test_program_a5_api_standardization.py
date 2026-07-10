from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from invyra_forecasting.api.app import app
from invyra_forecasting.api.production_contracts import (
    PRODUCTION_API_VERSION,
    PRODUCTION_CONTRACT_STABILITY,
    PRODUCTION_CONTRACT_VERSION,
    ProductionApiEnvelope,
    production_envelope,
)


def _client() -> TestClient:
    return TestClient(app)


def test_production_envelope_exposes_stable_contract_markers() -> None:
    payload = production_envelope("test_resource", {"status": "ok"})

    assert payload["api_version"] == PRODUCTION_API_VERSION
    assert payload["contract_version"] == PRODUCTION_CONTRACT_VERSION
    assert payload["contract_stability"] == PRODUCTION_CONTRACT_STABILITY
    assert payload["advisory_only"] is True
    assert payload["read_only"] is True
    assert payload["inventory_source_of_truth_preserved"] is True


def test_production_envelope_rejects_contract_marker_drift() -> None:
    with pytest.raises(ValueError, match="unsupported production API contract version"):
        ProductionApiEnvelope(
            api_version=PRODUCTION_API_VERSION,
            resource="test_resource",
            data={},
            contract_version="2.0.0",
        )

    with pytest.raises(ValueError, match="contract must remain stable"):
        ProductionApiEnvelope(
            api_version=PRODUCTION_API_VERSION,
            resource="test_resource",
            data={},
            contract_stability="experimental",
        )


def test_enterprise_v1_endpoints_share_contract_markers() -> None:
    for path in ("/v1", "/v1/models", "/v1/metrics", "/v1/observability/ping"):
        response = _client().get(path)

        assert response.status_code == 200
        payload = response.json()
        assert payload["api_version"] == PRODUCTION_API_VERSION
        assert payload["contract_version"] == PRODUCTION_CONTRACT_VERSION
        assert payload["contract_stability"] == PRODUCTION_CONTRACT_STABILITY
        assert payload["advisory_only"] is True
        assert payload["read_only"] is True
        assert payload["inventory_source_of_truth_preserved"] is True


def test_openapi_document_retains_versioned_enterprise_surface() -> None:
    response = _client().get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "Invyra Forecasting Engine"
    assert schema["info"]["version"]
    assert "/v1/forecast" in schema["paths"]
    assert "/v1/forecast/batch" in schema["paths"]
    assert "/v1/forecast/compare" in schema["paths"]
    assert "/v1/metrics" in schema["paths"]
    assert "/v1/observability/ping" in schema["paths"]
