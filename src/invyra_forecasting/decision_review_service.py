from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from invyra_forecasting.decision_gates import ForecastDecisionGateEvaluator
from invyra_forecasting.decision_review import ForecastDecisionReviewPacketBuilder
from invyra_forecasting.decision_review_queue import DecisionReviewQueueBuilder, DecisionReviewQueueItem
from invyra_forecasting.decision_review_store import InMemoryDecisionReviewQueueStore
from invyra_forecasting.models.contracts import ForecastModelOutput


@dataclass(frozen=True)
class ForecastDecisionReviewServiceResult:
    """Read-only service result for a submitted forecast review item."""

    queue_item: DecisionReviewQueueItem
    store: InMemoryDecisionReviewQueueStore

    def to_dict(self) -> dict[str, Any]:
        return {
            "queue_item": self.queue_item.to_dict(),
            "store_snapshot": self.store.snapshot().to_dict(),
            "advisory_only": True,
            "read_only": True,
            "inventory_source_of_truth_preserved": True,
        }


class ForecastDecisionReviewService:
    """Coordinates read-only forecast review preparation without operational mutation."""

    def __init__(
        self,
        *,
        gate_evaluator: ForecastDecisionGateEvaluator | None = None,
        packet_builder: ForecastDecisionReviewPacketBuilder | None = None,
        queue_builder: DecisionReviewQueueBuilder | None = None,
        store: InMemoryDecisionReviewQueueStore | None = None,
    ) -> None:
        self._gate_evaluator = gate_evaluator or ForecastDecisionGateEvaluator()
        self._packet_builder = packet_builder or ForecastDecisionReviewPacketBuilder()
        self._queue_builder = queue_builder or DecisionReviewQueueBuilder()
        self._store = store or InMemoryDecisionReviewQueueStore()

    @property
    def store(self) -> InMemoryDecisionReviewQueueStore:
        return self._store

    def prepare_review(
        self,
        *,
        queue_id: str,
        forecast: ForecastModelOutput,
        review_notes: tuple[str, ...] = (),
    ) -> ForecastDecisionReviewServiceResult:
        gate = self._gate_evaluator.evaluate(forecast)
        packet = self._packet_builder.build(forecast=forecast, decision_gate=gate, review_notes=review_notes)
        queue_item = self._queue_builder.build_item(queue_id=queue_id, packet=packet)
        updated_store = self._store.with_item(queue_item)
        return ForecastDecisionReviewServiceResult(queue_item=queue_item, store=updated_store)
