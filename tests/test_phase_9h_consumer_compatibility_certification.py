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


class _RoutingHttpClient:
    def __init__(self, api: TestClient) -> None:
        self._api = api
        self.requests: list[tuple[str, dict[str, Any]]] = []

    def get(self, path: str, **kwargs: Any) -> Any:
        self.requests.append((path, kwargs))
        return self._api.get(path, **kwargs)


def _store_with_item(*, item_id: str = "item-9h") -> InMemoryDecisionReviewQueueStore:
    forecast = ForecastModelOutput(
        item_id=item_id,
        location_id="store-1",
        environment=Environment.TEST,
        forecast_days=30,
        forecast_quantity=100.0,
        projected_days_of_cover=10.0,
        stockout_risk="LOW",
        confidence=0.80,
        explanation=("test forecast",),
        evidence_refs=("evidence::9h",),
        model_name="test_model",
        model_version="9H.test",
    )
    gate = ForecastDecisionGateEvaluator().evaluate(forecast)
    packet = ForecastDecisionReviewPacketBuilder().build(forecast=forecast, decision_gate=gate)
    item = DecisionReviewQueueBuilder().build_item(queue_id=f"queue-{item_id}", packet=packet)
    return InMemoryDecisionReviewQueueStore((item,))


def _api_client(store: InMemoryDecisionReviewQueueStore | None = None) -> TestClient:
    service = DecisionReviewEndpointProjectionService(queue_store=store or _store_with_item())
    return TestClient(create_decision_review_app(projection_service=service))


def test_reference_client_is_certified_against_live_endpoint_shapes() -> None:
    http_client = _RoutingHttpClient(_api_client())
    client = DecisionReviewReferenceClient(http_client)

    dashboard = client.get_dashboard()
    export_bundle = client.get_export_bundle()

    assert dashboard.response_version == "8H.1"
    assert dashboard.total_count == 1
    assert export_bundle.bundle_version == "8L.1"
    assert export_bundle.export_version == "8I.1"
    assert export_bundle.record_count == dashboard.total_count
    assert export_bundle.valid is True
    assert http_client.requests == [
        ("/forecast/decision-review/dashboard", {}),
        ("/forecast/decision-review/export", {"params": {"export_format": "json"}}),
    ]


def test_reference_client_certifies_dict_export_format_compatibility() -> None:
    http_client = _RoutingHttpClient(_api_client())
    client = DecisionReviewReferenceClient(http_client)

    export_bundle = client.get_export_bundle(export_format="dict")

    assert export_bundle.export_format == "dict"
    assert export_bundle.ready_for_delivery is True
    assert export_bundle.valid is True


def test_reference_client_tolerates_future_optional_dashboard_fields() -> None:
    payload = _api_client().get("/forecast/decision-review/dashboard").json()
    payload["future_optional_top_level"] = {"ignored": True}
    payload["dashboard"]["future_optional_dashboard_field"] = {"ignored": True}
    payload["dashboard"]["summary"]["future_optional_summary_field"] = 123
    payload["dashboard"]["snapshot"]["future_optional_snapshot_field"] = ["ignored"]

    view = parse_dashboard_payload(payload)

    assert view.response_version == "8H.1"
    assert view.total_count == 1
    assert len(view.items) == 1


def test_reference_client_tolerates_future_optional_export_fields() -> None:
    payload = _api_client().get("/forecast/decision-review/export").json()
    payload["future_optional_top_level"] = {"ignored": True}
    payload["export"]["future_optional_export_field"] = {"ignored": True}
    payload["manifest"]["future_optional_manifest_field"] = {"ignored": True}
    payload["validation"]["future_optional_validation_field"] = {"ignored": True}

    view = parse_export_bundle_payload(payload)

    assert view.bundle_version == "8L.1"
    assert view.record_count == 1
    assert view.valid is True


def test_reference_client_fails_closed_when_governance_flags_are_missing() -> None:
    payload = _api_client().get("/forecast/decision-review/dashboard").json()
    del payload["advisory_only"]

    with pytest.raises(DecisionReviewClientError, match="not marked advisory-only"):
        parse_dashboard_payload(payload)


def test_reference_client_fails_closed_when_required_version_changes_type() -> None:
    payload = _api_client().get("/forecast/decision-review/dashboard").json()
    payload["response_version"] = 9

    with pytest.raises(DecisionReviewClientError, match="response_version"):
        parse_dashboard_payload(payload)


def test_unsupported_export_format_remains_uncertified_for_reference_client() -> None:
    http_client = _RoutingHttpClient(_api_client())
    client = DecisionReviewReferenceClient(http_client)

    with pytest.raises(DecisionReviewClientError, match="Unexpected decision review response status: 400"):
        client.get_export_bundle(export_format="csv")
