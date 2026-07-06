from __future__ import annotations

from invyra_forecasting.constants import Environment
from invyra_forecasting.decision_gates import ForecastDecisionGateEvaluator
from invyra_forecasting.decision_review import ForecastDecisionReviewPacketBuilder
from invyra_forecasting.decision_review_api import DecisionReviewApiResponseBuilder
from invyra_forecasting.decision_review_dashboard import DecisionReviewDashboardProjectionBuilder
from invyra_forecasting.decision_review_queue import DecisionReviewQueueBuilder
from invyra_forecasting.decision_review_store import InMemoryDecisionReviewQueueStore
from invyra_forecasting.models.contracts import ForecastModelOutput


def _forecast() -> ForecastModelOutput:
    return ForecastModelOutput(
        item_id="item-1",
        location_id="store-1",
        environment=Environment.TEST,
        forecast_days=30,
        forecast_quantity=100.0,
        projected_days_of_cover=10.0,
        stockout_risk="LOW",
        confidence=0.80,
        explanation=("test forecast",),
        evidence_refs=("evidence::1",),
        model_name="test_model",
        model_version="8H.test",
    )


def _dashboard():
    forecast = _forecast()
    gate = ForecastDecisionGateEvaluator().evaluate(forecast)
    packet = ForecastDecisionReviewPacketBuilder().build(forecast=forecast, decision_gate=gate)
    item = DecisionReviewQueueBuilder().build_item(queue_id="queue-1", packet=packet)
    snapshot = InMemoryDecisionReviewQueueStore((item,)).snapshot()
    return DecisionReviewDashboardProjectionBuilder().build(snapshot)


def test_review_api_response_has_versioned_stable_shape() -> None:
    response = DecisionReviewApiResponseBuilder().build(_dashboard())

    payload = response.to_dict()

    assert payload["response_version"] == "8H.1"
    assert payload["dashboard"]["summary"]["total_count"] == 1
    assert payload["dashboard"]["snapshot"]["total_count"] == 1


def test_review_api_response_handles_empty_dashboard() -> None:
    dashboard = DecisionReviewDashboardProjectionBuilder().build(InMemoryDecisionReviewQueueStore().snapshot())

    response = DecisionReviewApiResponseBuilder().build(dashboard)

    assert response.dashboard.summary.total_count == 0
    assert response.to_dict()["dashboard"]["summary"]["total_count"] == 0


def test_review_api_response_serializes_governance_metadata() -> None:
    response = DecisionReviewApiResponseBuilder().build(_dashboard())

    payload = response.to_dict()

    assert payload["advisory_only"] is True
    assert payload["read_only"] is True
    assert payload["inventory_source_of_truth_preserved"] is True
    assert payload["dashboard"]["advisory_only"] is True
