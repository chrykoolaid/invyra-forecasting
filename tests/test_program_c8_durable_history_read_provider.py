from __future__ import annotations

from contextlib import contextmanager

from invyra_forecasting.api import tenant_context
from invyra_forecasting.explainability_archive import HistoricalExplainabilityRecord
from invyra_forecasting.history import ForecastHistoryRecord
from invyra_forecasting.history_provider import DurableHistoryReadProvider


@contextmanager
def _tenant(tenant_id: str | None):
    token = tenant_context._TENANT_ID.set(tenant_context.normalize_tenant_id(tenant_id))
    try:
        yield
    finally:
        tenant_context._TENANT_ID.reset(token)


def _history(
    history_id: str,
    *,
    forecast_id: str = "forecast-1",
    version_number: int = 1,
    parent_history_id: str | None = None,
    created_at_utc: str = "2026-07-14T10:00:00+00:00",
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
        created_at_utc=created_at_utc,
        snapshot_id="snapshot-1",
        evidence_refs=("evidence-1",),
    )


def _explainability(
    archive_id: str,
    *,
    history_id: str,
    forecast_id: str = "forecast-1",
    confidence: float = 0.82,
) -> HistoricalExplainabilityRecord:
    return HistoricalExplainabilityRecord(
        archive_id=archive_id,
        history_id=history_id,
        forecast_id=forecast_id,
        model_name="seasonal-naive",
        model_version="1.0",
        confidence=confidence,
        explanation=("Demand trend increased.",),
        evidence_refs=("evidence-1",),
        reasoning_summary=("Stable seasonal pattern.",),
        supporting_metrics={"mae": 1.25},
        archived_at_utc="2026-07-14T10:05:00+00:00",
    )


def test_provider_rehydrates_history_and_explainability(tmp_path):
    provider = DurableHistoryReadProvider.from_directories(
        history_dir=tmp_path / "history",
        explainability_dir=tmp_path / "explainability",
    )
    history = _history("history-1")
    explanation = _explainability("archive-1", history_id="history-1")
    provider.history_store.append(history)
    provider.explainability_store.append(explanation)

    service = provider.build_query_service()
    item = service.get("history-1")

    assert item["history"]["history_id"] == "history-1"
    assert item["explainability"]["archive_id"] == "archive-1"
    assert item["explainability"]["confidence"] == 0.82


def test_provider_rebuilds_cleanly_after_process_restart(tmp_path):
    history_dir = tmp_path / "history"
    explainability_dir = tmp_path / "explainability"
    first_provider = DurableHistoryReadProvider.from_directories(
        history_dir=history_dir,
        explainability_dir=explainability_dir,
    )
    first = _history("history-v1")
    second = _history(
        "history-v2",
        version_number=2,
        parent_history_id="history-v1",
        created_at_utc="2026-07-14T11:00:00+00:00",
    )
    first_provider.history_store.append(first)
    first_provider.history_store.append(second)

    restarted_provider = DurableHistoryReadProvider.from_directories(
        history_dir=history_dir,
        explainability_dir=explainability_dir,
    )
    service = restarted_provider.build_query_service()

    assert tuple(
        item["history"]["history_id"] for item in service.versions("forecast-1").items
    ) == ("history-v1", "history-v2")
    assert tuple(
        item["history"]["history_id"] for item in service.lineage("history-v2").items
    ) == ("history-v1", "history-v2")


def test_provider_is_tenant_isolated(tmp_path):
    provider = DurableHistoryReadProvider.from_directories(
        history_dir=tmp_path / "history",
        explainability_dir=tmp_path / "explainability",
    )

    with _tenant("alpha"):
        provider.history_store.append(_history("shared-id", forecast_id="forecast-alpha"))
        provider.explainability_store.append(
            _explainability(
                "shared-archive",
                history_id="shared-id",
                forecast_id="forecast-alpha",
                confidence=0.9,
            )
        )

    with _tenant("bravo"):
        provider.history_store.append(_history("shared-id", forecast_id="forecast-bravo"))
        provider.explainability_store.append(
            _explainability(
                "shared-archive",
                history_id="shared-id",
                forecast_id="forecast-bravo",
                confidence=0.4,
            )
        )

    with _tenant("alpha"):
        item = provider.build_query_service().get("shared-id")
        assert item["history"]["forecast_id"] == "forecast-alpha"
        assert item["explainability"]["confidence"] == 0.9

    with _tenant("bravo"):
        item = provider.build_query_service().get("shared-id")
        assert item["history"]["forecast_id"] == "forecast-bravo"
        assert item["explainability"]["confidence"] == 0.4


def test_provider_returns_empty_read_model_for_empty_namespace(tmp_path):
    provider = DurableHistoryReadProvider.from_directories(
        history_dir=tmp_path / "history",
        explainability_dir=tmp_path / "explainability",
    )

    with _tenant("empty"):
        result = provider.build_query_service().list()

    assert result.items == ()
    assert result.total == 0
    assert result.advisory_only is True
    assert result.read_only is True
    assert result.inventory_source_of_truth_preserved is True
