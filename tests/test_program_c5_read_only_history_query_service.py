from __future__ import annotations

from contextlib import contextmanager

import pytest

from invyra_forecasting.api import tenant_context
from invyra_forecasting.constants import Environment
from invyra_forecasting.explainability_archive import (
    HistoricalExplainabilityArchiveService,
    InMemoryHistoricalExplainabilityRepository,
)
from invyra_forecasting.history import ForecastHistoryRecord, InMemoryForecastHistoryRepository
from invyra_forecasting.history_index import HistoricalSnapshotIndex, HistoryIndexQuery
from invyra_forecasting.history_query import ReadOnlyForecastHistoryQueryService
from invyra_forecasting.models.contracts import ForecastModelOutput


@contextmanager
def _tenant(tenant_id: str | None):
    token = tenant_context._TENANT_ID.set(tenant_context.normalize_tenant_id(tenant_id))
    try:
        yield
    finally:
        tenant_context._TENANT_ID.reset(token)


def _record(
    history_id: str,
    *,
    forecast_id: str = "forecast-1",
    version_number: int = 1,
    parent_history_id: str | None = None,
    snapshot_id: str = "snapshot-1",
    created_at_utc: str = "2026-07-13T10:00:00+00:00",
) -> ForecastHistoryRecord:
    return ForecastHistoryRecord(
        history_id=history_id,
        forecast_id=forecast_id,
        item_id="ITEM-001",
        location_id="LOC-001",
        model_name="seasonal-naive",
        model_version="1.0",
        forecast_payload={"forecast_quantity": 12.0},
        version_number=version_number,
        parent_history_id=parent_history_id,
        snapshot_id=snapshot_id,
        created_at_utc=created_at_utc,
    )


def _output(confidence: float = 0.82) -> ForecastModelOutput:
    return ForecastModelOutput(
        item_id="ITEM-001",
        location_id="LOC-001",
        environment=Environment.TEST,
        forecast_days=7,
        forecast_quantity=12.0,
        projected_days_of_cover=4.5,
        stockout_risk="MEDIUM",
        confidence=confidence,
        explanation=("Demand trend increased.",),
        evidence_refs=("evidence-1",),
        model_name="seasonal-naive",
        model_version="1.0",
    )


def _service(records: tuple[ForecastHistoryRecord, ...]):
    history_repository = InMemoryForecastHistoryRepository()
    history_index = HistoricalSnapshotIndex()
    explainability_repository = InMemoryHistoricalExplainabilityRepository()
    for record in records:
        history_repository.append(record)
        history_index.add(record)
    return (
        ReadOnlyForecastHistoryQueryService(
            history_repository=history_repository,
            history_index=history_index,
            explainability_repository=explainability_repository,
        ),
        explainability_repository,
    )


def test_get_combines_history_and_archived_explainability():
    record = _record("history-1")
    service, explainability_repository = _service((record,))
    HistoricalExplainabilityArchiveService(explainability_repository).archive_output(
        archive_id="archive-1",
        history_id=record.history_id,
        forecast_id=record.forecast_id,
        output=_output(),
    )

    item = service.get("history-1")

    assert item["history"]["history_id"] == "history-1"
    assert item["explainability"]["archive_id"] == "archive-1"
    assert item["explainability"]["confidence"] == 0.82
    assert item["advisory_only"] is True
    assert item["read_only"] is True


def test_get_returns_none_for_missing_history():
    service, _ = _service(())

    assert service.get("missing") is None


def test_list_uses_index_filters_and_pagination():
    records = (
        _record("history-1", created_at_utc="2026-07-13T10:00:00+00:00"),
        _record(
            "history-2",
            forecast_id="forecast-2",
            snapshot_id="snapshot-2",
            created_at_utc="2026-07-13T11:00:00+00:00",
        ),
        _record(
            "history-3",
            forecast_id="forecast-3",
            snapshot_id="snapshot-2",
            created_at_utc="2026-07-13T12:00:00+00:00",
        ),
    )
    service, _ = _service(records)

    result = service.list(HistoryIndexQuery(snapshot_id="snapshot-2"), limit=1, offset=1)
    payload = result.to_dict()

    assert result.total == 2
    assert tuple(item["history"]["history_id"] for item in result.items) == ("history-3",)
    assert payload["pagination"] == {"limit": 1, "offset": 1, "total": 2}
    assert payload["inventory_source_of_truth_preserved"] is True


def test_versions_and_lineage_return_ordered_read_models():
    first = _record("history-v1")
    second = _record(
        "history-v2",
        version_number=2,
        parent_history_id="history-v1",
        created_at_utc="2026-07-13T11:00:00+00:00",
    )
    service, _ = _service((first, second))

    versions = service.versions("forecast-1")
    lineage = service.lineage("history-v2")

    expected = ("history-v1", "history-v2")
    assert tuple(item["history"]["history_id"] for item in versions.items) == expected
    assert tuple(item["history"]["history_id"] for item in lineage.items) == expected


def test_query_service_is_tenant_isolated():
    history_repository = InMemoryForecastHistoryRepository()
    history_index = HistoricalSnapshotIndex()
    explainability_repository = InMemoryHistoricalExplainabilityRepository()
    service = ReadOnlyForecastHistoryQueryService(
        history_repository=history_repository,
        history_index=history_index,
        explainability_repository=explainability_repository,
    )

    with _tenant("alpha"):
        alpha = _record("shared-id", forecast_id="forecast-alpha")
        history_repository.append(alpha)
        history_index.add(alpha)

    with _tenant("bravo"):
        bravo = _record("shared-id", forecast_id="forecast-bravo")
        history_repository.append(bravo)
        history_index.add(bravo)

    with _tenant("alpha"):
        assert service.get("shared-id")["history"]["forecast_id"] == "forecast-alpha"

    with _tenant("bravo"):
        assert service.get("shared-id")["history"]["forecast_id"] == "forecast-bravo"


def test_pagination_validation_rejects_invalid_values():
    service, _ = _service(())

    with pytest.raises(ValueError, match="limit must be greater than or equal to 1"):
        service.list(limit=0)

    with pytest.raises(ValueError, match="offset must be greater than or equal to 0"):
        service.list(offset=-1)
