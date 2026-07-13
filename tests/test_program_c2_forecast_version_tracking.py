from __future__ import annotations

from contextlib import contextmanager

import pytest

from invyra_forecasting.api import tenant_context
from invyra_forecasting.history import ForecastHistoryService, InMemoryForecastHistoryRepository


@contextmanager
def _tenant(tenant_id: str | None):
    token = tenant_context._TENANT_ID.set(tenant_context.normalize_tenant_id(tenant_id))
    try:
        yield
    finally:
        tenant_context._TENANT_ID.reset(token)


def _service() -> ForecastHistoryService:
    return ForecastHistoryService(InMemoryForecastHistoryRepository())


def _record_initial(service: ForecastHistoryService, history_id: str = "history-v1"):
    return service.record(
        history_id=history_id,
        forecast_id="forecast-1",
        item_id="ITEM-001",
        location_id="LOC-001",
        model_name="seasonal-naive",
        model_version="1.0",
        forecast_payload={"forecast_quantity": 10.0},
    )


def test_revise_creates_direct_parent_child_version_chain():
    service = _service()
    first = _record_initial(service)
    second = service.revise(
        first.history_id,
        history_id="history-v2",
        forecast_payload={"forecast_quantity": 12.0},
    )
    third = service.revise(
        second.history_id,
        history_id="history-v3",
        forecast_payload={"forecast_quantity": 14.0},
    )

    assert first.version_number == 1
    assert first.parent_history_id is None
    assert second.version_number == 2
    assert second.parent_history_id == first.history_id
    assert third.version_number == 3
    assert third.parent_history_id == second.history_id
    assert service.lineage(third.history_id) == (first, second, third)


def test_versions_and_latest_are_ordered_by_version_number():
    service = _service()
    first = _record_initial(service)
    second = service.revise(
        first.history_id,
        history_id="history-v2",
        forecast_payload={"forecast_quantity": 12.0},
    )

    assert service.versions_for_forecast("forecast-1") == (first, second)
    assert service.latest_for_forecast("forecast-1") == second
    assert service.latest_for_forecast("missing") is None


def test_duplicate_forecast_version_is_rejected():
    service = _service()
    _record_initial(service)

    with pytest.raises(
        ValueError,
        match=r"forecast history version already exists: forecast-1 v1",
    ):
        _record_initial(service, history_id="another-v1")


def test_parent_must_exist_and_belong_to_same_forecast():
    service = _service()
    parent = _record_initial(service)

    with pytest.raises(ValueError, match="parent history record does not exist: missing"):
        service.record(
            history_id="history-v2",
            forecast_id="forecast-1",
            item_id="ITEM-001",
            location_id="LOC-001",
            model_name="seasonal-naive",
            model_version="1.0",
            forecast_payload={"forecast_quantity": 12.0},
            version_number=2,
            parent_history_id="missing",
        )

    with pytest.raises(ValueError, match="parent history record must belong to the same forecast"):
        service.record(
            history_id="other-forecast-v2",
            forecast_id="forecast-2",
            item_id="ITEM-001",
            location_id="LOC-001",
            model_name="seasonal-naive",
            model_version="1.0",
            forecast_payload={"forecast_quantity": 12.0},
            version_number=2,
            parent_history_id=parent.history_id,
        )


def test_version_must_directly_follow_parent():
    service = _service()
    parent = _record_initial(service)

    with pytest.raises(ValueError, match="history version must directly follow its parent version"):
        service.record(
            history_id="history-v3",
            forecast_id="forecast-1",
            item_id="ITEM-001",
            location_id="LOC-001",
            model_name="seasonal-naive",
            model_version="1.0",
            forecast_payload={"forecast_quantity": 14.0},
            version_number=3,
            parent_history_id=parent.history_id,
        )


def test_version_lineage_is_tenant_isolated():
    repository = InMemoryForecastHistoryRepository()
    service = ForecastHistoryService(repository)

    with _tenant("alpha"):
        alpha_first = _record_initial(service, history_id="shared-v1")
        alpha_second = service.revise(
            alpha_first.history_id,
            history_id="shared-v2",
            forecast_payload={"forecast_quantity": 11.0},
        )

    with _tenant("bravo"):
        bravo_first = _record_initial(service, history_id="shared-v1")
        bravo_second = service.revise(
            bravo_first.history_id,
            history_id="shared-v2",
            forecast_payload={"forecast_quantity": 21.0},
        )

    with _tenant("alpha"):
        assert service.latest_for_forecast("forecast-1") == alpha_second

    with _tenant("bravo"):
        assert service.latest_for_forecast("forecast-1") == bravo_second
