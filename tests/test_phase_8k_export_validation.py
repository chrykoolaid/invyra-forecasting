from __future__ import annotations

from dataclasses import replace

from invyra_forecasting.constants import Environment
from invyra_forecasting.decision_gates import ForecastDecisionGateEvaluator
from invyra_forecasting.decision_review import ForecastDecisionReviewPacketBuilder
from invyra_forecasting.decision_review_api import DecisionReviewApiResponseBuilder
from invyra_forecasting.decision_review_dashboard import DecisionReviewDashboardProjectionBuilder
from invyra_forecasting.decision_review_export import DecisionReviewExportProjectionBuilder
from invyra_forecasting.decision_review_export_manifest import DecisionReviewExportManifestBuilder
from invyra_forecasting.decision_review_export_validation import DecisionReviewExportManifestValidator
from invyra_forecasting.decision_review_queue import DecisionReviewQueueBuilder
from invyra_forecasting.decision_review_store import InMemoryDecisionReviewQueueStore
from invyra_forecasting.models.contracts import ForecastModelOutput


def _manifest(item_count: int = 1):
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
            model_version="8K.test",
        )
        gate = ForecastDecisionGateEvaluator().evaluate(forecast)
        packet = ForecastDecisionReviewPacketBuilder().build(forecast=forecast, decision_gate=gate)
        items.append(DecisionReviewQueueBuilder().build_item(queue_id=f"queue-{index}", packet=packet))
    dashboard = DecisionReviewDashboardProjectionBuilder().build(InMemoryDecisionReviewQueueStore(tuple(items)).snapshot())
    response = DecisionReviewApiResponseBuilder().build(dashboard)
    export = DecisionReviewExportProjectionBuilder().build(response)
    return DecisionReviewExportManifestBuilder().build(export)


def test_export_manifest_validator_accepts_valid_manifest() -> None:
    result = DecisionReviewExportManifestValidator().validate(_manifest(item_count=2))

    assert result.valid is True
    assert result.warnings == ()


def test_export_manifest_validator_warns_on_record_count_mismatch() -> None:
    manifest = replace(_manifest(item_count=2), record_count=99)

    result = DecisionReviewExportManifestValidator().validate(manifest)

    assert result.valid is False
    assert result.warnings == ("Manifest record count does not match dashboard summary total count.",)


def test_export_manifest_validation_result_serializes_governance_metadata() -> None:
    result = DecisionReviewExportManifestValidator().validate(_manifest())

    payload = result.to_dict()

    assert payload["validation_version"] == "8K.1"
    assert payload["advisory_only"] is True
    assert payload["read_only"] is True
    assert payload["inventory_source_of_truth_preserved"] is True
