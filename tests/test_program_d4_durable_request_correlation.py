from __future__ import annotations

from contextlib import contextmanager

from invyra_forecasting.api import tenant_context
from invyra_forecasting.history import ForecastHistoryService, InMemoryForecastHistoryRepository
from invyra_forecasting.history_persistence import FileForecastHistoryRepository


@contextmanager
def _request(request_id: str | None):
    token = tenant_context._REQUEST_ID.set(request_id)
    try:
        yield
    finally:
        tenant_context._REQUEST_ID.reset(token)


def _record(service: ForecastHistoryService, history_id: str, **kwargs):
    return service.record(
        history_id=history_id,
        forecast_id="forecast-d4",
        item_id="ITEM-D4",
        location_id="LOC-D4",
        model_name="seasonal-naive",
        model_version="1.0",
        forecast_payload={"forecast_quantity": 12.0},
        **kwargs,
    )


def test_active_request_id_is_added_to_history_metadata() -> None:
    service = ForecastHistoryService()

    with _request("request-d4-create"):
        record = _record(service, "history-d4-create")

    assert record.metadata["request_id"] == "request-d4-create"


def test_history_created_outside_request_context_remains_compatible() -> None:
    service = ForecastHistoryService()

    record = _record(service, "history-d4-no-context", metadata={"source": "batch"})

    assert record.metadata == {"source": "batch"}


def test_explicit_request_metadata_is_not_overwritten() -> None:
    service = ForecastHistoryService()

    with _request("request-d4-active"):
        record = _record(
            service,
            "history-d4-explicit",
            metadata={"request_id": "request-d4-upstream", "source": "import"},
        )

    assert record.metadata == {
        "request_id": "request-d4-upstream",
        "source": "import",
    }


def test_revision_captures_its_own_request_id() -> None:
    repository = InMemoryForecastHistoryRepository()
    service = ForecastHistoryService(repository)

    with _request("request-d4-v1"):
        first = _record(service, "history-d4-v1")

    with _request("request-d4-v2"):
        second = service.revise(
            first.history_id,
            history_id="history-d4-v2",
            forecast_payload={"forecast_quantity": 14.0},
        )

    assert first.metadata["request_id"] == "request-d4-v1"
    assert second.metadata["request_id"] == "request-d4-v2"


def test_request_id_survives_file_persistence_round_trip(tmp_path) -> None:
    service = ForecastHistoryService()

    with _request("request-d4-durable"):
        record = _record(service, "history-d4-durable")

    repository = FileForecastHistoryRepository(tmp_path)
    repository.append(record)

    restarted = FileForecastHistoryRepository(tmp_path)
    assert restarted.get(record.history_id).metadata["request_id"] == "request-d4-durable"


def test_request_correlation_preserves_enterprise_guardrails() -> None:
    service = ForecastHistoryService()

    with _request("request-d4-guardrails"):
        record = _record(service, "history-d4-guardrails")

    assert record.advisory_only is True
    assert record.read_only is True
    assert record.inventory_source_of_truth_preserved is True
