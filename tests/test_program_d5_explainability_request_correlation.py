from __future__ import annotations

from contextlib import contextmanager

from invyra_forecasting.api import tenant_context
from invyra_forecasting.constants import Environment
from invyra_forecasting.explainability_archive import HistoricalExplainabilityArchiveService
from invyra_forecasting.explainability_persistence import FileHistoricalExplainabilityRepository
from invyra_forecasting.models.contracts import ForecastModelOutput


@contextmanager
def _request(request_id: str | None):
    token = tenant_context._REQUEST_ID.set(request_id)
    try:
        yield
    finally:
        tenant_context._REQUEST_ID.reset(token)


def _output() -> ForecastModelOutput:
    return ForecastModelOutput(
        item_id="ITEM-001",
        location_id="LOC-001",
        environment=Environment.TEST,
        forecast_days=7,
        forecast_quantity=12.0,
        projected_days_of_cover=4.5,
        stockout_risk="MEDIUM",
        confidence=0.82,
        explanation=("Demand trend increased.",),
        evidence_refs=("evidence-1",),
        model_name="seasonal-naive",
        model_version="1.0",
    )


def test_archive_captures_active_request_id() -> None:
    service = HistoricalExplainabilityArchiveService()

    with _request("request-d5-create"):
        record = service.archive_output(
            archive_id="archive-d5-create",
            history_id="history-d5-create",
            forecast_id="forecast-d5-create",
            output=_output(),
        )

    assert record.metadata["request_id"] == "request-d5-create"


def test_archive_without_request_context_preserves_compatibility() -> None:
    service = HistoricalExplainabilityArchiveService()

    record = service.archive_output(
        archive_id="archive-d5-none",
        history_id="history-d5-none",
        forecast_id="forecast-d5-none",
        output=_output(),
    )

    assert record.metadata == {}


def test_explicit_request_id_metadata_is_not_overwritten() -> None:
    service = HistoricalExplainabilityArchiveService()

    with _request("request-d5-active"):
        record = service.archive_output(
            archive_id="archive-d5-explicit",
            history_id="history-d5-explicit",
            forecast_id="forecast-d5-explicit",
            output=_output(),
            metadata={"request_id": "request-d5-explicit", "source": "test"},
        )

    assert record.metadata == {"request_id": "request-d5-explicit", "source": "test"}


def test_request_id_survives_file_persistence(tmp_path) -> None:
    service = HistoricalExplainabilityArchiveService()
    with _request("request-d5-durable"):
        record = service.archive_output(
            archive_id="archive-d5-durable",
            history_id="history-d5-durable",
            forecast_id="forecast-d5-durable",
            output=_output(),
        )

    repository = FileHistoricalExplainabilityRepository(tmp_path)
    repository.append(record)
    loaded = FileHistoricalExplainabilityRepository(tmp_path).get(record.archive_id)

    assert loaded is not None
    assert loaded.metadata["request_id"] == "request-d5-durable"
    assert loaded.advisory_only is True
    assert loaded.read_only is True
    assert loaded.inventory_source_of_truth_preserved is True
