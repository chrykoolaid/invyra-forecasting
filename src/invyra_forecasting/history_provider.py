from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from invyra_forecasting.explainability_archive import InMemoryHistoricalExplainabilityRepository
from invyra_forecasting.explainability_persistence import FileHistoricalExplainabilityRepository
from invyra_forecasting.history import InMemoryForecastHistoryRepository
from invyra_forecasting.history_index import HistoricalSnapshotIndex
from invyra_forecasting.history_persistence import FileForecastHistoryRepository
from invyra_forecasting.history_query import ReadOnlyForecastHistoryQueryService


@dataclass(frozen=True)
class DurableHistoryReadProvider:
    """Restart-safe, tenant-aware composition for read-only forecast history access."""

    history_store: FileForecastHistoryRepository
    explainability_store: FileHistoricalExplainabilityRepository

    @classmethod
    def from_directories(
        cls,
        *,
        history_dir: str | Path = "data/history",
        explainability_dir: str | Path = "data/explainability",
    ) -> "DurableHistoryReadProvider":
        return cls(
            history_store=FileForecastHistoryRepository(history_dir),
            explainability_store=FileHistoricalExplainabilityRepository(explainability_dir),
        )

    def build_query_service(self) -> ReadOnlyForecastHistoryQueryService:
        history_repository = InMemoryForecastHistoryRepository()
        history_index = HistoricalSnapshotIndex()
        explainability_repository = InMemoryHistoricalExplainabilityRepository()

        for record in self.history_store.all():
            history_repository.append(record)
            history_index.add(record)

        self.explainability_store.load_into(explainability_repository)

        return ReadOnlyForecastHistoryQueryService(
            history_repository=history_repository,
            history_index=history_index,
            explainability_repository=explainability_repository,
        )
