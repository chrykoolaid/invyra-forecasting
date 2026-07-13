from __future__ import annotations

from contextlib import contextmanager

import pytest

from invyra_forecasting.api import tenant_context
from invyra_forecasting.explainability_archive import (
    HistoricalExplainabilityRecord,
    InMemoryHistoricalExplainabilityRepository,
)
from invyra_forecasting.explainability_persistence import (
    FileHistoricalExplainabilityRepository,
)


@contextmanager
def _tenant(tenant_id: str | None):
    token = tenant_context._TENANT_ID.set(tenant_context.normalize_tenant_id(tenant_id))
    try:
        yield
    finally:
        tenant_context._TENANT_ID.reset(token)


def _record(
    archive_id: str,
    *,
    history_id: str = "history-1",
    forecast_id: str = "forecast-1",
    confidence: float = 0.82,
    archived_at_utc: str = "2026-07-13T10:00:00+00:00",
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
        archived_at_utc=archived_at_utc,
    )


def test_default_namespace_round_trips_at_root(tmp_path):
    repository = FileHistoricalExplainabilityRepository(tmp_path)
    record = _record("archive-1")

    with _tenant(None):
        repository.append(record)
        loaded = repository.get("archive-1")
        path = repository.path_for("archive-1")

    assert path == tmp_path / "archive-1.json"
    assert loaded == record
    assert loaded.explanation == ("Demand trend increased.",)
    assert loaded.supporting_metrics == {"mae": 1.25}


def test_named_tenants_use_isolated_encoded_directories(tmp_path):
    repository = FileHistoricalExplainabilityRepository(tmp_path)

    with _tenant("region/a"):
        alpha = _record("shared-id", history_id="shared-history", confidence=0.9)
        repository.append(alpha)
        alpha_path = repository.path_for("shared-id")

    with _tenant("bravo"):
        bravo = _record("shared-id", history_id="shared-history", confidence=0.4)
        repository.append(bravo)
        bravo_path = repository.path_for("shared-id")

    assert alpha_path == tmp_path / "region%2Fa" / "shared-id.json"
    assert bravo_path == tmp_path / "bravo" / "shared-id.json"

    with _tenant("region/a"):
        assert repository.get("shared-id") == alpha
        assert repository.for_history("shared-history").confidence == 0.9

    with _tenant("bravo"):
        assert repository.get("shared-id") == bravo
        assert repository.for_history("shared-history").confidence == 0.4


def test_duplicate_archive_and_history_are_rejected(tmp_path):
    repository = FileHistoricalExplainabilityRepository(tmp_path)
    first = _record("archive-1")
    repository.append(first)

    with pytest.raises(ValueError, match="explainability archive already exists: archive-1"):
        repository.append(first)

    with pytest.raises(
        ValueError,
        match="history record already has explainability archived: history-1",
    ):
        repository.append(_record("archive-2"))


def test_forecast_timeline_survives_repository_restart(tmp_path):
    repository = FileHistoricalExplainabilityRepository(tmp_path)
    first = _record("archive-1", history_id="history-1")
    second = _record(
        "archive-2",
        history_id="history-2",
        archived_at_utc="2026-07-13T11:00:00+00:00",
    )
    repository.append(first)
    repository.append(second)

    restarted = FileHistoricalExplainabilityRepository(tmp_path)

    assert restarted.for_forecast("forecast-1") == (first, second)


def test_all_is_sorted_by_timestamp_then_archive_id(tmp_path):
    repository = FileHistoricalExplainabilityRepository(tmp_path)
    late = _record(
        "late",
        history_id="history-late",
        forecast_id="forecast-late",
        archived_at_utc="2026-07-13T12:00:00+00:00",
    )
    early_b = _record(
        "early-b",
        history_id="history-early-b",
        forecast_id="forecast-early-b",
        archived_at_utc="2026-07-13T10:00:00+00:00",
    )
    early_a = _record(
        "early-a",
        history_id="history-early-a",
        forecast_id="forecast-early-a",
        archived_at_utc="2026-07-13T10:00:00+00:00",
    )

    for record in (late, early_b, early_a):
        repository.append(record)

    assert tuple(record.archive_id for record in repository.all()) == (
        "early-a",
        "early-b",
        "late",
    )


def test_load_into_rehydrates_in_memory_archive(tmp_path):
    file_repository = FileHistoricalExplainabilityRepository(tmp_path)
    first = _record("archive-1", history_id="history-1")
    second = _record(
        "archive-2",
        history_id="history-2",
        forecast_id="forecast-2",
    )
    file_repository.append(first)
    file_repository.append(second)

    memory_repository = InMemoryHistoricalExplainabilityRepository()
    count = file_repository.load_into(memory_repository)

    assert count == 2
    assert memory_repository.for_history("history-1") == first
    assert memory_repository.for_history("history-2") == second
