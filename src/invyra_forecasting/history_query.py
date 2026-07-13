from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from invyra_forecasting.explainability_archive import InMemoryHistoricalExplainabilityRepository
from invyra_forecasting.history import InMemoryForecastHistoryRepository
from invyra_forecasting.history_index import HistoricalSnapshotIndex, HistoryIndexQuery


@dataclass(frozen=True)
class HistoryQueryResult:
    items: tuple[dict[str, Any], ...]
    total: int
    limit: int
    offset: int
    advisory_only: bool = True
    read_only: bool = True
    inventory_source_of_truth_preserved: bool = True

    def __post_init__(self) -> None:
        if self.limit < 1:
            raise ValueError("limit must be greater than or equal to 1")
        if self.offset < 0:
            raise ValueError("offset must be greater than or equal to 0")
        if self.total < 0:
            raise ValueError("total must be greater than or equal to 0")
        if not self.advisory_only:
            raise ValueError("history queries must remain advisory-only")
        if not self.read_only:
            raise ValueError("history queries must remain read-only")
        if not self.inventory_source_of_truth_preserved:
            raise ValueError("inventory source of truth must be preserved")

    def to_dict(self) -> dict[str, Any]:
        return {
            "items": list(self.items),
            "pagination": {
                "limit": self.limit,
                "offset": self.offset,
                "total": self.total,
            },
            "advisory_only": self.advisory_only,
            "read_only": self.read_only,
            "inventory_source_of_truth_preserved": self.inventory_source_of_truth_preserved,
        }


class ReadOnlyForecastHistoryQueryService:
    """Dependency-injected read model over immutable history and explainability archives."""

    def __init__(
        self,
        *,
        history_repository: InMemoryForecastHistoryRepository,
        history_index: HistoricalSnapshotIndex,
        explainability_repository: InMemoryHistoricalExplainabilityRepository,
    ) -> None:
        self._history_repository = history_repository
        self._history_index = history_index
        self._explainability_repository = explainability_repository

    def get(self, history_id: str) -> dict[str, Any] | None:
        record = self._history_repository.get(history_id)
        if record is None:
            return None
        return self._build_item(record.history_id)

    def list(
        self,
        query: HistoryIndexQuery | None = None,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> HistoryQueryResult:
        if limit < 1:
            raise ValueError("limit must be greater than or equal to 1")
        if offset < 0:
            raise ValueError("offset must be greater than or equal to 0")

        records = self._history_index.query(query or HistoryIndexQuery())
        total = len(records)
        selected = records[offset : offset + limit]
        items = tuple(self._build_item(record.history_id) for record in selected)
        return HistoryQueryResult(items=items, total=total, limit=limit, offset=offset)

    def versions(self, forecast_id: str) -> HistoryQueryResult:
        records = self._history_repository.versions_for_forecast(forecast_id)
        items = tuple(self._build_item(record.history_id) for record in records)
        return HistoryQueryResult(items=items, total=len(items), limit=max(1, len(items)), offset=0)

    def lineage(self, history_id: str) -> HistoryQueryResult:
        records = self._history_repository.lineage(history_id)
        items = tuple(self._build_item(record.history_id) for record in records)
        return HistoryQueryResult(items=items, total=len(items), limit=max(1, len(items)), offset=0)

    def _build_item(self, history_id: str) -> dict[str, Any]:
        record = self._history_repository.get(history_id)
        if record is None:
            raise ValueError(f"history record not found: {history_id}")
        explainability = self._explainability_repository.for_history(history_id)
        return {
            "history": record.to_dict(),
            "explainability": None if explainability is None else explainability.to_dict(),
            "advisory_only": True,
            "read_only": True,
            "inventory_source_of_truth_preserved": True,
        }
