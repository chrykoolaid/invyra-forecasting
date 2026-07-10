from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from invyra_forecasting.api.app import app
from invyra_forecasting.api.production_contracts import (
    CONTRACT_STABILITY,
    CONTRACT_VERSION,
    production_error_envelope,
)


def _client() -> TestClient:
    return TestClient(app)


def test_all_v1_envelopes_expose_stable_contract_markers() -> None:
    payload = _client().get("/v1").json()

    assert payload["api_version"] == "v1"
    assert payload["contract_version"] == CONTRACT_VERSION
    assert payload["contract_stability"] == CONTRACT_STABILITY
    assert payload["advisory_only"] is True
    assert payload["read_only"] is True
    assert payload["inventory_source_of_truth_preserved"] is True


def test_operational_endpoint_inherits_standard_contract_markers() -> None:
    payload = _client().get("/v1/observability/ping").json()

    assert payload["contract_version"] == CONTRACT_VERSION
    assert payload["contract_stability"] == CONTRACT_STABILITY
    assert payload["resource"] == "observability_ping"


def test_standard_error_envelope_preserves_enterprise_guardrails() -> None:
    payload = production_error_envelope(
        status_code=404,
        code="resource_not_found",
        message="The requested resource was not found.",
        details={"resource_id": "missing-1"},
    )

    assert payload["resource"] == "error"
    assert payload["contract_version"] == CONTRACT_VERSION
    assert payload["contract_stability"] == CONTRACT_STABILITY
    assert payload["advisory_only"] is True
    assert payload["read_only"] is True
    assert payload["inventory_source_of_truth_preserved"] is True
    assert payload["data"] == {
        "status_code": 404,
        "code": "resource_not_found",
        "message": "The requested resource was not found.",
        "details": {"resource_id": "missing-1"},
    }


def test_error_envelope_rejects_non_error_status_codes() -> None:
    with pytest.raises(ValueError, match="status_code must be between 400 and 599"):
        production_error_envelope(status_code=200, code="not_an_error", message="invalid")
