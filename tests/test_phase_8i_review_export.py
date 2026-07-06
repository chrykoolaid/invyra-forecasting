from __future__ import annotations

import pytest

from invyra_forecasting.constants import Environment
from invyra_forecasting.decision_gates import ForecastDecisionGateEvaluator
from invyra_forecasting.decision_review import ForecastDecisionReviewPacketBuilder
from invyra_forecasting.decision_review_api import DecisionReviewApiResponseBuilder
from invyra_forecasting.decision_review_dashboard import DecisionReviewDashboardProjectionBuilder
from invyra_forecasting.decision_review_export import DecisionReviewExportProjectionBuilder
from invyra_forecasting.decision_review_queue import DecisionReviewQueueBuilder
from invyra_forecasting.decision_review_store import InMemoryDecisionReviewQueueStore
from invyra_forecasting.models.contracts import ForecastModelOutput


def _response():
    forecast = ForecastModelOutput(
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
        model_version="8I.test",
    )
    gate = ForecastDecisionGateEvaluator().evaluate(forecast)
    packet = ForecastDecisionReviewPacketBuilder().build(forecast=forecast, decision_gate=gate)
    item = DecisionReviewQueueBuilder().build_item(queue_id="queue-1", packet=packet)
    dashboard = DecisionReviewDashboardProjectionBuilder().build(InMemoryDecisionReviewQueueStore((item,)).snapshot())
    return DecisionReviewApiResponseBuilder().build(dashboard)


def test_review_export_defaults_to_json_projection() -> None:
    export = DecisionReviewExportProjectionBuilder().build(_response())

    payload = export.to_dict()

    assert payload["export_format"] == "json"
    assert payload["export_version"] == "8I.1"
    assert payload["response"]["dashboard"]["summary"]["total_count"] == 1


def test_review_export_accepts_dict_format_case_insensitively() -> None:
    export = DecisionReviewExportProjectionBuilder().build(_response(), export_format=" DICT ")

    assert export.export_format == "dict"


def test_review_export_rejects_unsupported_format() -> None:
    with pytest.raises(ValueError, match="Unsupported decision review export format"):
        DecisionReviewExportProjectionBuilder().build(_response(), export_format="csv")


def test_review_export_serializes_governance_metadata() -> None:
    export = DecisionReviewExportProjectionBuilder().build(_response())

    payload = export.to_dict()

    assert payload["advisory_only"] is True
    assert payload["read_only"] is True
    assert payload["inventory_source_of_truth_preserved"] is True
    assert payload["response"]["advisory_only"] is True
