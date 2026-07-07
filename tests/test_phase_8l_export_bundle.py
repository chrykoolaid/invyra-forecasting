from __future__ import annotations

from invyra_forecasting.constants import Environment
from invyra_forecasting.decision_gates import ForecastDecisionGateEvaluator
from invyra_forecasting.decision_review import ForecastDecisionReviewPacketBuilder
from invyra_forecasting.decision_review_api import DecisionReviewApiResponseBuilder
from invyra_forecasting.decision_review_dashboard import DecisionReviewDashboardProjectionBuilder
from invyra_forecasting.decision_review_export import DecisionReviewExportProjectionBuilder
from invyra_forecasting.decision_review_export_bundle import DecisionReviewExportBundleBuilder
from invyra_forecasting.decision_review_queue import DecisionReviewQueueBuilder
from invyra_forecasting.decision_review_store import InMemoryDecisionReviewQueueStore
from invyra_forecasting.models.contracts import ForecastModelOutput


def _export(item_count: int = 1):
    items = []
    for index in range(item_count):
        forecast = ForecastModelOutput(
            item_id=f"item-{index}",
            location_id="store-1",
            environment=Environment.TEST,
            forecast_days=30,
            forecast_quantity=100.0,
            projected_days_of_cover=10.0,
            stockout_risk="LOW",
            confidence=0.80,
            explanation=("test forecast",),
            evidence_refs=(f"evidence::{index}",),
            model_name="test_model",
            model_version="8L.test",
        )
        gate = ForecastDecisionGateEvaluator().evaluate(forecast)
        packet = ForecastDecisionReviewPacketBuilder().build(forecast=forecast, decision_gate=gate)
        items.append(DecisionReviewQueueBuilder().build_item(queue_id=f"queue-{index}", packet=packet))
    dashboard = DecisionReviewDashboardProjectionBuilder().build(InMemoryDecisionReviewQueueStore(tuple(items)).snapshot())
    response = DecisionReviewApiResponseBuilder().build(dashboard)
    return DecisionReviewExportProjectionBuilder().build(response)


def test_export_bundle_marks_valid_export_ready_for_delivery() -> None:
    bundle = DecisionReviewExportBundleBuilder().build(_export(item_count=2))

    assert bundle.ready_for_delivery is True
    assert bundle.manifest.record_count == 2
    assert bundle.validation.valid is True
    assert bundle.validation.warnings == ()


def test_export_bundle_handles_empty_export() -> None:
    bundle = DecisionReviewExportBundleBuilder().build(_export(item_count=0))

    assert bundle.ready_for_delivery is True
    assert bundle.manifest.record_count == 0


def test_export_bundle_serializes_governance_metadata() -> None:
    bundle = DecisionReviewExportBundleBuilder().build(_export())

    payload = bundle.to_dict()

    assert payload["bundle_version"] == "8L.1"
    assert payload["advisory_only"] is True
    assert payload["read_only"] is True
    assert payload["inventory_source_of_truth_preserved"] is True
    assert payload["export"]["advisory_only"] is True
    assert payload["manifest"]["advisory_only"] is True
    assert payload["validation"]["advisory_only"] is True
