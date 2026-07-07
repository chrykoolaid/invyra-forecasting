from __future__ import annotations

import pytest
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


def _store_with_item() -> InMemoryDecisionReviewQueueStore:
    forecast = ForecastModelOutput(
        item_id="item-9a",
        location_id="store-1",
        environment=Environment.TEST,
        forecast_days=30,
        forecast_quantity=100.0,
        projected_days_of_cover=10.0,
        stockout_risk="LOW",
        confidence=0.80,
        explanation=("test forecast",),
        evidence_refs=("evidence::9a",),
        model_name="test_model",
        model_version="9A.test",
    )
    gate = ForecastDecisionGateEvaluator().evaluate(forecast)
    packet = ForecastDecisionReviewPacketBuilder().build(forecast=forecast, decision_gate=gate)
    item = DecisionReviewQueueBuilder().build_item(queue_id="queue-9a", packet=packet)
    return InMemoryDecisionReviewQueueStore((item,))


def _client(store: InMemoryDecisionReviewQueueStore | None = None) -> TestClient:
    service = DecisionReviewEndpointProjectionService(queue_store=store or InMemoryDecisionReviewQueueStore())
    return TestClient(create_decision_review_app(projection_service=service))


def test_decision_review_dashboard_endpoint_exposes_existing_projection_shape() -> None:
    response = _client(_store_with_item()).get("/forecast/decision-review/dashboard")

    assert response.status_code == 200
    payload = response.json()
    assert payload["response_version"] == "8H.1"
    assert payload["dashboard"]["summary"]["total_count"] == 1
    assert payload["dashboard"]["snapshot"]["total_count"] == 1
    assert payload["advisory_only"] is True
    assert payload["read_only"] is True
    assert payload["inventory_source_of_truth_preserved"] is True


def test_decision_review_dashboard_endpoint_handles_empty_queue() -> None:
    response = _client().get("/forecast/decision-review/dashboard")

    assert response.status_code == 200
    payload = response.json()
    assert payload["dashboard"]["summary"]["total_count"] == 0
    assert payload["dashboard"]["snapshot"]["total_count"] == 0


def test_decision_review_export_endpoint_exposes_existing_bundle_projection() -> None:
    response = _client(_store_with_item()).get("/forecast/decision-review/export")

    assert response.status_code == 200
    payload = response.json()
    assert payload["bundle_version"] == "8L.1"
    assert payload["ready_for_delivery"] is True
    assert payload["export"]["export_version"] == "8I.1"
    assert payload["export"]["response"]["response_version"] == "8H.1"
    assert payload["manifest"]["record_count"] == 1
    assert payload["validation"]["valid"] is True
    assert payload["advisory_only"] is True
    assert payload["read_only"] is True
    assert payload["inventory_source_of_truth_preserved"] is True


def test_decision_review_export_endpoint_supports_dict_projection_format() -> None:
    response = _client(_store_with_item()).get("/forecast/decision-review/export", params={"export_format": "dict"})

    assert response.status_code == 200
    assert response.json()["export"]["export_format"] == "dict"


def test_decision_review_export_endpoint_rejects_unsupported_format_without_mutation() -> None:
    response = _client(_store_with_item()).get("/forecast/decision-review/export", params={"export_format": "csv"})

    assert response.status_code == 500
