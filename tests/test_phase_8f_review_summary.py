from __future__ import annotations

from invyra_forecasting.constants import Environment
from invyra_forecasting.decision_gates import ForecastDecisionGateEvaluator
from invyra_forecasting.decision_review import ForecastDecisionReviewPacketBuilder
from invyra_forecasting.decision_review_queue import DecisionReviewQueueBuilder
from invyra_forecasting.decision_review_store import InMemoryDecisionReviewQueueStore
from invyra_forecasting.decision_review_summary import DecisionReviewSummaryBuilder
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
        model_version="8F.test",
    )


def _item(queue_id: str, forecast: ForecastModelOutput):
    gate = ForecastDecisionGateEvaluator().evaluate(forecast)
    packet = ForecastDecisionReviewPacketBuilder().build(forecast=forecast, decision_gate=gate)
    return DecisionReviewQueueBuilder().build_item(queue_id=queue_id, packet=packet)


def test_review_summary_handles_empty_snapshot() -> None:
    snapshot = InMemoryDecisionReviewQueueStore().snapshot()

    summary = DecisionReviewSummaryBuilder().build(snapshot)

    assert summary.total_count == 0
    assert summary.ready_count == 0
    assert summary.pending_count == 0
    assert summary.needs_more_evidence_count == 0


def test_review_summary_counts_statuses_and_priorities() -> None:
    ready_normal = _item("ready-normal", _forecast())
    pending_normal = _item("pending-normal", _forecast(confidence=0.20))
    evidence_normal = _item("evidence-normal", _forecast(evidence_refs=()))
    ready_medium = _item("ready-medium", _forecast(stockout_risk="HIGH"))
    ready_high = _item("ready-high", _forecast(stockout_risk="CRITICAL", confidence=0.90))
    snapshot = InMemoryDecisionReviewQueueStore(
        (ready_normal, pending_normal, evidence_normal, ready_medium, ready_high)
    ).snapshot()

    summary = DecisionReviewSummaryBuilder().build(snapshot)

    assert summary.total_count == 5
    assert summary.ready_count == 3
    assert summary.pending_count == 1
    assert summary.needs_more_evidence_count == 1
    assert summary.high_priority_count == 1
    assert summary.medium_priority_count == 1
    assert summary.normal_priority_count == 3


def test_review_summary_serializes_governance_metadata() -> None:
    summary = DecisionReviewSummaryBuilder().build(InMemoryDecisionReviewQueueStore().snapshot())

    payload = summary.to_dict()

    assert payload["advisory_only"] is True
    assert payload["read_only"] is True
    assert payload["inventory_source_of_truth_preserved"] is True
