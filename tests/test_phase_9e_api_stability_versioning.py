from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from fastapi.testclient import TestClient

from invyra_forecasting.constants import Environment
from invyra_forecasting.decision_gates import ForecastDecisionGateEvaluator
from invyra_forecasting.decision_review import ForecastDecisionReviewPacketBuilder
from invyra_forecasting.decision_review_endpoints import (
    DecisionReviewEndpointProjectionService,
    create_decision_review_app,
)
from invyra_forecasting.decision_review_queue import DecisionReviewQueueBuilder
from invyra_forecasting.decision_review_store import InMemoryDecisionReviewQueueStore
from invyra_forecasting.models.contracts import ForecastModelOutput


REQUIRED_GOVERNANCE_FLAGS = (
    "advisory_only",
    "read_only",
    "inventory_source_of_truth_preserved",
)


def _store_with_item() -> InMemoryDecisionReviewQueueStore:
    forecast = ForecastModelOutput(
        item_id="item-9e",
        location_id="store-1",
        environment=Environment.TEST,
        forecast_days=30,
        forecast_quantity=100.0,
        projected_days_of_cover=10.0,
        stockout_risk="LOW",
        confidence=0.80,
        explanation=("test forecast",),
        evidence_refs=("evidence::9e",),
        model_name="test_model",
        model_version="9E.test",
    )
    gate = ForecastDecisionGateEvaluator().evaluate(forecast)
    packet = ForecastDecisionReviewPacketBuilder().build(forecast=forecast, decision_gate=gate)
    item = DecisionReviewQueueBuilder().build_item(queue_id="queue-9e", packet=packet)
    return InMemoryDecisionReviewQueueStore((item,))


def _client(store: InMemoryDecisionReviewQueueStore | None = None) -> TestClient:
    service = DecisionReviewEndpointProjectionService(queue_store=store or InMemoryDecisionReviewQueueStore())
    return TestClient(create_decision_review_app(projection_service=service))


def _assert_required_governance_flags(payload: Mapping[str, Any]) -> None:
    for flag in REQUIRED_GOVERNANCE_FLAGS:
        assert payload[flag] is True


def test_dashboard_endpoint_keeps_stable_http_contract() -> None:
    response = _client(_store_with_item()).get("/forecast/decision-review/dashboard")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")


def test_export_endpoint_keeps_stable_http_contract() -> None:
    response = _client(_store_with_item()).get("/forecast/decision-review/export")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")


def test_dashboard_endpoint_keeps_stable_response_version_contract() -> None:
    payload = _client(_store_with_item()).get("/forecast/decision-review/dashboard").json()

    assert payload["response_version"] == "8H.1"
    assert "dashboard" in payload
    _assert_required_governance_flags(payload)
    _assert_required_governance_flags(payload["dashboard"])


def test_export_endpoint_keeps_stable_version_contract() -> None:
    payload = _client(_store_with_item()).get("/forecast/decision-review/export").json()

    assert payload["bundle_version"] == "8L.1"
    assert payload["export"]["export_version"] == "8I.1"
    assert payload["export"]["response"]["response_version"] == "8H.1"
    _assert_required_governance_flags(payload)
    _assert_required_governance_flags(payload["export"])
    _assert_required_governance_flags(payload["manifest"])
    _assert_required_governance_flags(payload["validation"])


def test_dashboard_response_retains_required_backward_compatible_fields() -> None:
    payload = _client(_store_with_item()).get("/forecast/decision-review/dashboard").json()
    dashboard = payload["dashboard"]

    assert set(payload) >= {
        "response_version",
        "dashboard",
        "generated_at",
        *REQUIRED_GOVERNANCE_FLAGS,
    }
    assert set(dashboard) >= {
        "summary",
        "snapshot",
        "generated_at",
        *REQUIRED_GOVERNANCE_FLAGS,
    }
    assert set(dashboard["summary"]) >= {
        "total_count",
        "status_counts",
        "priority_counts",
        "generated_at",
        *REQUIRED_GOVERNANCE_FLAGS,
    }
    assert set(dashboard["snapshot"]) >= {
        "total_count",
        "items",
        *REQUIRED_GOVERNANCE_FLAGS,
    }


def test_export_response_retains_required_backward_compatible_fields() -> None:
    payload = _client(_store_with_item()).get("/forecast/decision-review/export").json()

    assert set(payload) >= {
        "bundle_version",
        "ready_for_delivery",
        "export",
        "manifest",
        "validation",
        "generated_at",
        *REQUIRED_GOVERNANCE_FLAGS,
    }
    assert set(payload["export"]) >= {
        "export_format",
        "export_version",
        "response",
        "generated_at",
        *REQUIRED_GOVERNANCE_FLAGS,
    }
    assert set(payload["manifest"]) >= {
        "manifest_version",
        "export_version",
        "export_format",
        "record_count",
        "generated_at",
        *REQUIRED_GOVERNANCE_FLAGS,
    }
    assert set(payload["validation"]) >= {
        "valid",
        "warnings",
        "validation_version",
        "generated_at",
        *REQUIRED_GOVERNANCE_FLAGS,
    }


def test_downstream_client_can_ignore_unknown_fields() -> None:
    payload = _client(_store_with_item()).get("/forecast/decision-review/dashboard").json()
    payload["future_optional_field"] = {"ignored_by": "compatible_clients"}

    adapter_projection = {
        "response_version": payload["response_version"],
        "total_count": payload["dashboard"]["summary"]["total_count"],
        "advisory_only": payload["advisory_only"],
        "read_only": payload["read_only"],
        "inventory_source_of_truth_preserved": payload["inventory_source_of_truth_preserved"],
    }

    assert adapter_projection == {
        "response_version": "8H.1",
        "total_count": 1,
        "advisory_only": True,
        "read_only": True,
        "inventory_source_of_truth_preserved": True,
    }


def test_unsupported_export_format_keeps_stable_http_validation_contract() -> None:
    response = _client(_store_with_item()).get(
        "/forecast/decision-review/export",
        params={"export_format": "csv"},
    )

    assert response.status_code == 400
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {"detail": "Unsupported decision review export format"}
