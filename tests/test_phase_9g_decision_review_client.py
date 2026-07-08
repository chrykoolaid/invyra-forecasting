from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from invyra_forecasting.constants import Environment
from invyra_forecasting.decision_gates import ForecastDecisionGateEvaluator
from invyra_forecasting.decision_review import ForecastDecisionReviewPacketBuilder
from invyra_forecasting.decision_review_client import (
    DecisionReviewClientError,
    DecisionReviewReferenceClient,
    assert_read_only_governance,
    parse_dashboard_payload,
    parse_export_bundle_payload,
)
from invyra_forecasting.decision_review_endpoints import (
    DecisionReviewEndpointProjectionService,
    create_decision_review_app,
)
from invyra_forecasting.decision_review_queue import DecisionReviewQueueBuilder
from invyra_forecasting.decision_review_store import InMemoryDecisionReviewQueueStore
from invyra_forecasting.models.contracts import ForecastModelOutput


class _Response:
    def __init__(self, *, status_code: int, payload: dict[str, Any]) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict[str, Any]:
        return self._payload


class _FakeHttpClient:
    def __init__(self, responses: dict[str, _Response]) -> None:
        self.responses = responses
        self.requests: list[tuple[str, dict[str, Any]]] = []

    def get(self, path: str, **kwargs: Any) -> _Response:
        self.requests.append((path, kwargs))
        return self.responses[path]


def _store_with_item() -> InMemoryDecisionReviewQueueStore:
    forecast = ForecastModelOutput(
        item_id="item-9g",
        location_id="store-1",
        environment=Environment.TEST,
        forecast_days=30,
        forecast_quantity=100.0,
        projected_days_of_cover=10.0,
        stockout_risk="LOW",
        confidence=0.80,
        explanation=("test forecast",),
        evidence_refs=("evidence::9g",),
        model_name="test_model",
        model_version="9G.test",
    )
    gate = ForecastDecisionGateEvaluator().evaluate(forecast)
    packet = ForecastDecisionReviewPacketBuilder().build(forecast=forecast, decision_gate=gate)
    item = DecisionReviewQueueBuilder().build_item(queue_id="queue-9g", packet=packet)
    return InMemoryDecisionReviewQueueStore((item,))


def _api_client() -> TestClient:
    service = DecisionReviewEndpointProjectionService(queue_store=_store_with_item())
    return TestClient(create_decision_review_app(projection_service=service))


def test_parse_dashboard_payload_returns_downstream_view() -> None:
    payload = _api_client().get("/forecast/decision-review/dashboard").json()

    view = parse_dashboard_payload(payload)

    assert view.response_version == "8H.1"
    assert view.total_count == 1
    assert view.ready_count == 1
    assert view.pending_count == 0
    assert view.needs_more_evidence_count == 0
    assert len(view.items) == 1


def test_parse_export_bundle_payload_returns_downstream_view() -> None:
    payload = _api_client().get("/forecast/decision-review/export").json()

    view = parse_export_bundle_payload(payload)

    assert view.bundle_version == "8L.1"
    assert view.export_version == "8I.1"
    assert view.export_format == "json"
    assert view.ready_for_delivery is True
    assert view.record_count == 1
    assert view.valid is True
    assert view.warnings == ()


def test_reference_client_loads_dashboard_and_export_without_mutation() -> None:
    api = _api_client()
    http_client = _FakeHttpClient(
        {
            "/forecast/decision-review/dashboard": _Response(
                status_code=200,
                payload=api.get("/forecast/decision-review/dashboard").json(),
            ),
            "/forecast/decision-review/export": _Response(
                status_code=200,
                payload=api.get("/forecast/decision-review/export").json(),
            ),
        }
    )
    client = DecisionReviewReferenceClient(http_client)

    dashboard = client.get_dashboard()
    export = client.get_export_bundle(export_format="dict")

    assert dashboard.total_count == 1
    assert export.ready_for_delivery is True
    assert http_client.requests == [
        ("/forecast/decision-review/dashboard", {}),
        ("/forecast/decision-review/export", {"params": {"export_format": "dict"}}),
    ]


def test_client_rejects_non_read_only_payload() -> None:
    payload = _api_client().get("/forecast/decision-review/dashboard").json()
    payload["read_only"] = False

    with pytest.raises(DecisionReviewClientError, match="not marked read-only"):
        assert_read_only_governance(payload)


def test_client_rejects_unexpected_status() -> None:
    http_client = _FakeHttpClient(
        {
            "/forecast/decision-review/dashboard": _Response(
                status_code=500,
                payload={"detail": "unexpected"},
            )
        }
    )
    client = DecisionReviewReferenceClient(http_client)

    with pytest.raises(DecisionReviewClientError, match="Unexpected decision review response status"):
        client.get_dashboard()


def test_client_ignores_unknown_optional_fields() -> None:
    payload = _api_client().get("/forecast/decision-review/dashboard").json()
    payload["future_optional_field"] = {"safe_to_ignore": True}

    view = parse_dashboard_payload(payload)

    assert view.total_count == 1
