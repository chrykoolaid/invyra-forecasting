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


def _store_with_item() -> InMemoryDecisionReviewQueueStore:
    forecast = ForecastModelOutput(
        item_id="item-9d",
        location_id="store-1",
        environment=Environment.TEST,
        forecast_days=30,
        forecast_quantity=100.0,
        projected_days_of_cover=10.0,
        stockout_risk="LOW",
        confidence=0.80,
        explanation=("test forecast",),
        evidence_refs=("evidence::9d",),
        model_name="test_model",
        model_version="9D.test",
    )
    gate = ForecastDecisionGateEvaluator().evaluate(forecast)
    packet = ForecastDecisionReviewPacketBuilder().build(forecast=forecast, decision_gate=gate)
    item = DecisionReviewQueueBuilder().build_item(queue_id="queue-9d", packet=packet)
    return InMemoryDecisionReviewQueueStore((item,))


def _client(store: InMemoryDecisionReviewQueueStore | None = None) -> TestClient:
    service = DecisionReviewEndpointProjectionService(queue_store=store or InMemoryDecisionReviewQueueStore())
    return TestClient(create_decision_review_app(projection_service=service))


def _assert_governance_flags(payload: Mapping[str, Any]) -> None:
    assert payload["advisory_only"] is True
    assert payload["read_only"] is True
    assert payload["inventory_source_of_truth_preserved"] is True


def test_dashboard_payload_supports_documented_downstream_adapter_guardrails() -> None:
    payload = _client(_store_with_item()).get("/forecast/decision-review/dashboard").json()

    _assert_governance_flags(payload)
    _assert_governance_flags(payload["dashboard"])
    _assert_governance_flags(payload["dashboard"]["summary"])
    _assert_governance_flags(payload["dashboard"]["snapshot"])

    assert payload["dashboard"]["summary"]["total_count"] == 1
    assert payload["dashboard"]["snapshot"]["total_count"] == 1
    assert isinstance(payload["dashboard"]["snapshot"]["items"], list)


def test_export_payload_supports_documented_downstream_adapter_guardrails() -> None:
    payload = _client(_store_with_item()).get("/forecast/decision-review/export").json()

    _assert_governance_flags(payload)
    _assert_governance_flags(payload["export"])
    _assert_governance_flags(payload["export"]["response"])
    _assert_governance_flags(payload["manifest"])
    _assert_governance_flags(payload["validation"])

    assert payload["ready_for_delivery"] is True
    assert payload["manifest"]["record_count"] == 1
    assert payload["validation"]["valid"] is True


def test_export_payload_dict_format_remains_projection_only() -> None:
    response = _client(_store_with_item()).get(
        "/forecast/decision-review/export",
        params={"export_format": "dict"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["export"]["export_format"] == "dict"
    _assert_governance_flags(payload)
    _assert_governance_flags(payload["export"])


def test_unsupported_export_format_has_stable_validation_contract() -> None:
    response = _client(_store_with_item()).get(
        "/forecast/decision-review/export",
        params={"export_format": "csv"},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Unsupported decision review export format"}
