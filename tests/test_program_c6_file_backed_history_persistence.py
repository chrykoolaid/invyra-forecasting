from __future__ import annotations

from contextlib import contextmanager

import pytest

from invyra_forecasting.api import tenant_context
from invyra_forecasting.history import ForecastHistoryRecord, InMemoryForecastHistoryRepository
from invyra_forecasting.history_persistence import FileForecastHistoryRepository


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
        created_at_utc=created_at_utc,
        snapshot_id="snapshot-1",
        evidence_refs=("evidence-1",),
        metadata={"source": "test"},
    )


def test_default_namespace_preserves_root_layout_and_round_trips(tmp_path):
    repository = FileForecastHistoryRepository(tmp_path)
    record = _record("history-1")

    with _tenant(None):
        repository.append(record)
        path = repository.path_for(record.history_id)
        loaded = repository.get(record.history_id)

    assert path == tmp_path / "history-1.json"
    assert loaded == record
    assert loaded.evidence_refs == ("evidence-1",)
    assert loaded.metadata == {"source": "test"}


def test_named_tenants_use_isolated_encoded_directories(tmp_path):
    repository = FileForecastHistoryRepository(tmp_path)

    with _tenant("region/a"):
        alpha = _record("shared-id", forecast_id="forecast-alpha")
        repository.append(alpha)
        alpha_path = repository.path_for("shared-id")

    with _tenant("bravo"):
        bravo = _record("shared-id", forecast_id="forecast-bravo")
        repository.append(bravo)
        bravo_path = repository.path_for("shared-id")

    assert alpha_path == tmp_path / "region%2Fa" / "shared-id.json"
    assert bravo_path == tmp_path / "bravo" / "shared-id.json"

    with _tenant("region/a"):
        assert repository.get("shared-id") == alpha
        assert repository.versions_for_forecast("forecast-bravo") == ()

    with _tenant("bravo"):
        assert repository.get("shared-id") == bravo
        assert repository.versions_for_forecast("forecast-alpha") == ()


def test_append_rejects_duplicate_history_id_and_forecast_version(tmp_path):
    repository = FileForecastHistoryRepository(tmp_path)
    first = _record("history-1")
    repository.append(first)

    with pytest.raises(ValueError, match="history record already exists: history-1"):
        repository.append(first)

    with pytest.raises(
        ValueError,
        match=r"forecast history version already exists: forecast-1 v1",
    ):
        repository.append(_record("another-history-1"))


def test_parent_validation_and_lineage_survive_repository_restart(tmp_path):
    repository = FileForecastHistoryRepository(tmp_path)
    first = _record("history-v1")
    second = _record(
        "history-v2",
        version_number=2,
        parent_history_id="history-v1",
        created_at_utc="2026-07-13T11:00:00+00:00",
    )
    repository.append(first)
    repository.append(second)

    restarted = FileForecastHistoryRepository(tmp_path)

    assert restarted.versions_for_forecast("forecast-1") == (first, second)
    assert restarted.latest_for_forecast("forecast-1") == second
    assert restarted.lineage("history-v2") == (first, second)


def test_missing_parent_is_rejected_without_writing_file(tmp_path):
    repository = FileForecastHistoryRepository(tmp_path)
    child = _record(
        "history-v2",
        version_number=2,
        parent_history_id="missing",
    )

    with pytest.raises(ValueError, match="parent history record does not exist: missing"):
        repository.append(child)

    assert not repository.path_for("history-v2").exists()


def test_all_is_sorted_by_timestamp_then_history_id(tmp_path):
    repository = FileForecastHistoryRepository(tmp_path)
    late = _record(
        "late",
        forecast_id="forecast-late",
        created_at_utc="2026-07-13T12:00:00+00:00",
    )
    early_b = _record(
        "early-b",
        forecast_id="forecast-early-b",
        created_at_utc="2026-07-13T10:00:00+00:00",
    )
    early_a = _record(
        "early-a",
        forecast_id="forecast-early-a",
        created_at_utc="2026-07-13T10:00:00+00:00",
    )

    for record in (late, early_b, early_a):
        repository.append(record)

    assert tuple(record.history_id for record in repository.all()) == (
        "early-a",
        "early-b",
        "late",
    )


def test_load_into_rehydrates_append_compatible_repository(tmp_path):
    file_repository = FileForecastHistoryRepository(tmp_path)
    first = _record("history-1", forecast_id="forecast-1")
    second = _record("history-2", forecast_id="forecast-2")
    file_repository.append(first)
    file_repository.append(second)

    memory_repository = InMemoryForecastHistoryRepository()
    count = file_repository.load_into(memory_repository)

    assert count == 2
    assert memory_repository.all() == (first, second)
