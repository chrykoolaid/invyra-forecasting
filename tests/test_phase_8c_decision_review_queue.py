from __future__ import annotations

from invyra_forecasting.constants import Environment
from invyra_forecasting.decision_gates import ForecastDecisionGateEvaluator
from invyra_forecasting.decision_review import ForecastDecisionReviewPacketBuilder
from invyra_forecasting.decision_review_queue import DecisionReviewQueueBuilder, DecisionReviewQueueStatus
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
        model_version="8C.test",
    )


def _packet(forecast: ForecastModelOutput):
    gate = ForecastDecisionGateEvaluator().evaluate(forecast)
    return ForecastDecisionReviewPacketBuilder().build(forecast=forecast, decision_gate=gate)


def test_queue_item_marks_ready_packet_for_operator_review() -> None:
    packet = _packet(_forecast())

    item = DecisionReviewQueueBuilder().build_item(queue_id="queue-1", packet=packet)

    assert item.status == DecisionReviewQueueStatus.READY_FOR_OPERATOR_REVIEW
    assert item.priority == "NORMAL"
    assert item.queue_id == "queue-1"


def test_queue_item_marks_missing_evidence_packet_as_needing_more_evidence() -> None:
    packet = _packet(_forecast(evidence_refs=()))

    item = DecisionReviewQueueBuilder().build_item(queue_id="queue-2", packet=packet)

    assert item.status == DecisionReviewQueueStatus.NEEDS_MORE_EVIDENCE


def test_queue_item_marks_low_confidence_packet_as_pending_review() -> None:
    packet = _packet(_forecast(confidence=0.20))

    item = DecisionReviewQueueBuilder().build_item(queue_id="queue-3", packet=packet)

    assert item.status == DecisionReviewQueueStatus.PENDING_REVIEW


def test_queue_priority_tracks_stockout_risk_without_mutation() -> None:
    high_packet = _packet(_forecast(stockout_risk="HIGH"))
    critical_packet = _packet(_forecast(stockout_risk="CRITICAL", confidence=0.90))

    high_item = DecisionReviewQueueBuilder().build_item(queue_id="queue-high", packet=high_packet)
    critical_item = DecisionReviewQueueBuilder().build_item(queue_id="queue-critical", packet=critical_packet)

    assert high_item.priority == "MEDIUM"
    assert critical_item.priority == "HIGH"


def test_queue_item_serializes_governance_metadata() -> None:
    item = DecisionReviewQueueBuilder().build_item(queue_id="queue-4", packet=_packet(_forecast()))
    payload = item.to_dict()

    assert payload["advisory_only"] is True
    assert payload["read_only"] is True
    assert payload["inventory_source_of_truth_preserved"] is True
    assert payload["status"] == "READY_FOR_OPERATOR_REVIEW"
