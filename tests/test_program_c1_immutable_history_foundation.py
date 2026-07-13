from __future__ import annotations

from contextlib import contextmanager
from dataclasses import FrozenInstanceError

import pytest

from invyra_forecasting.api import tenant_context
from invyra_forecasting.history import (
    ForecastHistoryRecord,
    ForecastHistoryService,
    InMemoryForecastHistoryRepository,
)


@contextmanager
def _tenant(tenant_id: str | None):
    token = tenant_context._TENANT_ID.set(tenant_context.normalize_tenant_id(tenant_id))
    try:
        yield
    finally:
        tenant_context._TENANT_ID.reset(token)


def _record(history_id: str, forecast_id: str) -> ForecastHistoryRecord:
    return ForecastHistoryRecord(
        history_id=history_id,
        forecast_id=forecast_id,
        item_id="ITEM-001",
        location_id="LOC-001",
        model_name="seasonal-naive",
        model_version="1.0",
        forecast_payload={"forecast_quantity": 12.0, "confidence": 0.8},
        snapshot_id="SNAP-001",
        evidence_refs=("evidence-1",),
    )


def test_history_record_is_immutable_and_read_only():
    record = _record("history-1", "forecast-1")

    with pytest.raises(FrozenInstanceError):
        record.forecast_id = "changed"

    assert record.advisory_only is True
    assert record.read_only is True
    assert record.inventory_source_of_truth_preserved is True


def test_repository_is_append_only_and_rejects_duplicate_ids():
    repository = InMemoryForecastHistoryRepository()
    record = _record("history-1", "forecast-1")

    repository.append(record)

    with pytest.raises(ValueError, match="history record already exists: history-1"):
        repository.append(record)

    assert repository.get("history-1") == record


def test_history_is_isolated_by_tenant_namespace():
    repository = InMemoryForecastHistoryRepository()

    with _tenant("alpha"):
        repository.append(_record("shared-id", "forecast-alpha"))

    with _tenant("bravo"):
        repository.append(_record("shared-id", "forecast-bravo"))

    with _tenant("alpha"):
        assert repository.get("shared-id").forecast_id == "forecast-alpha"

    with _tenant("bravo"):
        assert repository.get("shared-id").forecast_id == "forecast-bravo"


def test_default_namespace_isolated_from_named_tenants():
    repository = InMemoryForecastHistoryRepository()

    with _tenant(None):
        repository.append(_record("default-history", "forecast-default"))
        assert len(repository.all()) == 1

    with _tenant("alpha"):
        assert repository.get("default-history") is None
        assert repository.all() == ()


def test_service_generates_unique_history_ids_and_utc_timestamps():
    service = ForecastHistoryService()

    first = service.record(
        forecast_id="forecast-1",
        item_id="ITEM-001",
        location_id="LOC-001",
        model_name="seasonal-naive",
        model_version="1.0",
        forecast_payload={"forecast_quantity": 12.0},
    )
    second = service.record(
        forecast_id="forecast-2",
        item_id="ITEM-001",
        location_id="LOC-001",
        model_name="seasonal-naive",
        model_version="1.0",
        forecast_payload={"forecast_quantity": 13.0},
    )

    assert first.history_id != second.history_id
    assert first.created_at_utc.endswith("+00:00")
    assert second.created_at_utc.endswith("+00:00")
    assert len(service.all()) == 2


def test_record_serialization_preserves_evidence_and_payload():
    payload = _record("history-1", "forecast-1").to_dict()

    assert payload["forecast_payload"] == {"forecast_quantity": 12.0, "confidence": 0.8}
    assert payload["evidence_refs"] == ["evidence-1"]
    assert payload["snapshot_id"] == "SNAP-001"
