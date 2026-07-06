from __future__ import annotations

from invyra_forecasting.constants import Environment
from invyra_forecasting.decision_gates import ForecastDecisionGateEvaluator
from invyra_forecasting.decision_review import ForecastDecisionReviewPacketBuilder
from invyra_forecasting.decision_review_dashboard import DecisionReviewDashboardProjectionBuilder
from invyra_forecasting.decision_review_queue import DecisionReviewQueueBuilder
from invyra_forecasting.decision_review_store import InMemoryDecisionReviewQueueStore
from invyra_forecasting.models.contracts import ForecastModelOutput


def _forecast(
    *,
    confidence: float = 0.80,
    evidence_refs: tuple[str, ...] = ("evidence::1",),
    stockout_risk: str = "LOW",
) -> ForecastModelOutput:
    return ForecastModelOutput(
        item_id="item-1",
        location_id="store-1",
        environment=Environment.TEST,
        forecast_days=30,
        forecast_quantity=100.0,
        projected_days_of_cover=10.0,
        stockout_risk=stockout_risk,
        confidence=confidence,
        explanation=("test forecast",),
        evidence_refs=evidence_refs,
        model_name="test_model",
        model_version="8G.test",
    )


def _item(queue_id: str, forecast: ForecastModelOutput):
    gate = ForecastDecisionGateEvaluator().evaluate(forecast)
    packet = ForecastDecisionReviewPacketBuilder().build(forecast=forecast, decision_gate=gate)
    return DecisionReviewQueueBuilder().build_item(queue_id=queue_id, packet=packet)


def test_dashboard_projection_combines_snapshot_and_summary() -> None:
    ready = _item("ready", _forecast())
    missing_evidence = _item("missing-evidence", _forecast(evidence_refs=()))
    snapshot = InMemoryDecisionReviewQueueStore((ready, missing_evidence)).snapshot()

    projection = DecisionReviewDashboardProjectionBuilder().build(snapshot)

    assert projection.snapshot.total_count == 2
    assert projection.summary.total_count == 2
    assert projection.summary.ready_count == 1
    assert projection.summary.needs_more_evidence_count == 1


def test_dashboard_projection_handles_empty_snapshot() -> None:
    snapshot = InMemoryDecisionReviewQueueStore().snapshot()

    projection = DecisionReviewDashboardProjectionBuilder().build(snapshot)

    assert projection.snapshot.total_count == 0
    assert projection.summary.total_count == 0


def test_dashboard_projection_serializes_governance_metadata() -> None:
    projection = DecisionReviewDashboardProjectionBuilder().build(InMemoryDecisionReviewQueueStore().snapshot())

    payload = projection.to_dict()

    assert payload["advisory_only"] is True
    assert payload["read_only"] is True
    assert payload["inventory_source_of_truth_preserved"] is True
    assert payload["summary"]["total_count"] == 0
    assert payload["snapshot"]["total_count"] == 0
