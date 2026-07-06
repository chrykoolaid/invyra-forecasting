from __future__ import annotations

from invyra_forecasting.constants import Environment
from invyra_forecasting.decision_review_queue import DecisionReviewQueueStatus
from invyra_forecasting.decision_review_service import ForecastDecisionReviewService
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
        model_version="8E.test",
    )


def test_review_service_prepares_ready_queue_item() -> None:
    service = ForecastDecisionReviewService()

    result = service.prepare_review(queue_id="queue-1", forecast=_forecast())

    assert result.queue_item.queue_id == "queue-1"
    assert result.queue_item.status == DecisionReviewQueueStatus.READY_FOR_OPERATOR_REVIEW
    assert result.queue_item.priority == "NORMAL"
    assert result.store.snapshot().total_count == 1


def test_review_service_keeps_original_store_unchanged() -> None:
    original_store = InMemoryDecisionReviewQueueStore()
    service = ForecastDecisionReviewService(store=original_store)

    result = service.prepare_review(queue_id="queue-1", forecast=_forecast())

    assert original_store.snapshot().total_count == 0
    assert service.store.snapshot().total_count == 0
    assert result.store.snapshot().total_count == 1


def test_review_service_propagates_gate_warnings_to_packet() -> None:
    service = ForecastDecisionReviewService()

    result = service.prepare_review(queue_id="queue-2", forecast=_forecast(evidence_refs=()))

    assert result.queue_item.status == DecisionReviewQueueStatus.NEEDS_MORE_EVIDENCE
    assert result.queue_item.packet.decision_gate.warnings


def test_review_service_accepts_review_notes_without_mutating_forecast() -> None:
    service = ForecastDecisionReviewService()

    result = service.prepare_review(
        queue_id="queue-3",
        forecast=_forecast(stockout_risk="HIGH"),
        review_notes=("Operator should review supplier lead time.",),
    )

    assert result.queue_item.priority == "MEDIUM"
    assert "Operator should review supplier lead time." in result.queue_item.packet.review_notes


def test_review_service_result_serializes_governance_metadata() -> None:
    service = ForecastDecisionReviewService()

    result = service.prepare_review(queue_id="queue-4", forecast=_forecast())
    payload = result.to_dict()

    assert payload["advisory_only"] is True
    assert payload["read_only"] is True
    assert payload["inventory_source_of_truth_preserved"] is True
    assert payload["store_snapshot"]["total_count"] == 1
