from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from invyra_forecasting.decision_review_queue import DecisionReviewQueueItem, DecisionReviewQueueStatus


@dataclass(frozen=True)
class DecisionReviewQueueSnapshot:
    """Read-only snapshot of queued forecast review items."""

    items: tuple[DecisionReviewQueueItem, ...]

    @property
    def total_count(self) -> int:
        return len(self.items)

    def by_status(self, status: DecisionReviewQueueStatus) -> tuple[DecisionReviewQueueItem, ...]:
        return tuple(item for item in self.items if item.status == status)

    def to_dict(self) -> dict[str, object]:
        return {
            "total_count": self.total_count,
            "items": [item.to_dict() for item in self.items],
            "advisory_only": True,
            "read_only": True,
            "inventory_source_of_truth_preserved": True,
        }


class InMemoryDecisionReviewQueueStore:
    """In-memory read-only review queue store for presentation workflows."""

    def __init__(self, items: Iterable[DecisionReviewQueueItem] = ()) -> None:
        self._items = tuple(items)

    def snapshot(self) -> DecisionReviewQueueSnapshot:
        return DecisionReviewQueueSnapshot(items=self._items)

    def list_items(
        self,
        *,
        status: DecisionReviewQueueStatus | None = None,
        priority: str | None = None,
    ) -> tuple[DecisionReviewQueueItem, ...]:
        items = self._items
        if status is not None:
            items = tuple(item for item in items if item.status == status)
        if priority is not None:
            normalized_priority = priority.upper()
            items = tuple(item for item in items if item.priority.upper() == normalized_priority)
        return items

    def with_item(self, item: DecisionReviewQueueItem) -> "InMemoryDecisionReviewQueueStore":
        """Return a new store containing the item without mutating this store."""

        existing = {queued.queue_id: queued for queued in self._items}
        existing[item.queue_id] = item
        return InMemoryDecisionReviewQueueStore(existing.values())
