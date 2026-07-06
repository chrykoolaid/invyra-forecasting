from __future__ import annotations

from invyra_forecasting.constants import Environment
from invyra_forecasting.decision_gates import ForecastDecisionGateEvaluator
from invyra_forecasting.decision_review import ForecastDecisionReviewPacketBuilder
from invyra_forecasting.decision_review_queue import DecisionReviewQueueBuilder, DecisionReviewQueueStatus
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
        model_version="8D.test",
    )


def _item(queue_id: str, forecast: ForecastModelOutput):
    gate = ForecastDecisionGateEvaluator().evaluate(forecast)
    packet = ForecastDecisionReviewPacketBuilder().build(forecast=forecast, decision_gate=gate)
    return DecisionReviewQueueBuilder().build_item(queue_id=queue_id, packet=packet)


def test_review_store_snapshot_lists_all_items() -> None:
    first = _item("queue-1", _forecast())
    second = _item("queue-2", _forecast(confidence=0.20))
    store = InMemoryDecisionReviewQueueStore((first, second))

    snapshot = store.snapshot()

    assert snapshot.total_count == 2
    assert snapshot.items == (first, second)


def test_review_store_filters_by_status_and_priority() -> None:
    ready = _item("queue-ready", _forecast())
    missing_evidence = _item("queue-evidence", _forecast(evidence_refs=()))
    high_priority = _item("queue-critical", _forecast(stockout_risk="CRITICAL", confidence=0.90))
    store = InMemoryDecisionReviewQueueStore((ready, missing_evidence, high_priority))

    evidence_items = store.list_items(status=DecisionReviewQueueStatus.NEEDS_MORE_EVIDENCE)
    high_items = store.list_items(priority="high")

    assert evidence_items == (missing_evidence,)
    assert high_items == (high_priority,)


def test_review_store_with_item_returns_new_store_without_mutating_original() -> None:
    first = _item("queue-1", _forecast())
    second = _item("queue-2", _forecast(confidence=0.20))
    original = InMemoryDecisionReviewQueueStore((first,))

    updated = original.with_item(second)

    assert original.snapshot().items == (first,)
    assert updated.snapshot().items == (first, second)


def test_review_store_replaces_duplicate_queue_id_in_new_store() -> None:
    original_item = _item("queue-1", _forecast(confidence=0.20))
    replacement_item = _item("queue-1", _forecast())
    store = InMemoryDecisionReviewQueueStore((original_item,))

    updated = store.with_item(replacement_item)

    assert updated.snapshot().items == (replacement_item,)


def test_review_store_snapshot_serializes_governance_metadata() -> None:
    store = InMemoryDecisionReviewQueueStore((_item("queue-1", _forecast()),))

    payload = store.snapshot().to_dict()

    assert payload["total_count"] == 1
    assert payload["advisory_only"] is True
    assert payload["read_only"] is True
    assert payload["inventory_source_of_truth_preserved"] is True
