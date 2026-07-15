from __future__ import annotations

from contextlib import contextmanager

from fastapi.testclient import TestClient

from invyra_forecasting.api import tenant_context
from invyra_forecasting.api.app import app
from invyra_forecasting.constants import Environment
from invyra_forecasting.explainability_archive import HistoricalExplainabilityArchiveService
from invyra_forecasting.explainability_persistence import FileHistoricalExplainabilityRepository
from invyra_forecasting.history import ForecastHistoryService
from invyra_forecasting.history_persistence import FileForecastHistoryRepository
from invyra_forecasting.history_provider import DurableHistoryReadProvider
from invyra_forecasting.models.contracts import ForecastModelOutput


@contextmanager
def _request_context(request_id: str, tenant_id: str | None = None):
    request_token = tenant_context._REQUEST_ID.set(request_id)
    tenant_token = tenant_context._TENANT_ID.set(tenant_context.normalize_tenant_id(tenant_id))
    try:
        yield
    finally:
        tenant_context._TENANT_ID.reset(tenant_token)
        tenant_context._REQUEST_ID.reset(request_token)


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


def test_request_id_is_consistent_across_response_history_and_explainability(tmp_path) -> None:
    request_id = "request-d7-certified"
    history_service = ForecastHistoryService()
    explainability_service = HistoricalExplainabilityArchiveService()

    with _request_context(request_id):
        history = history_service.record(
            history_id="history-d7",
            forecast_id="forecast-d7",
            item_id="ITEM-001",
            location_id="LOC-001",
            model_name="seasonal-naive",
            model_version="1.0",
            forecast_payload={"forecast_quantity": 12.0},
            evidence_refs=("evidence-1",),
        )
        explanation = explainability_service.archive_output(
            archive_id="archive-d7",
            history_id=history.history_id,
            forecast_id=history.forecast_id,
            output=_output(),
        )

    history_store = FileForecastHistoryRepository(tmp_path / "history")
    explainability_store = FileHistoricalExplainabilityRepository(tmp_path / "explainability")
    history_store.append(history)
    explainability_store.append(explanation)

    item = DurableHistoryReadProvider.from_directories(
        history_dir=tmp_path / "history",
        explainability_dir=tmp_path / "explainability",
    ).build_query_service().get(history.history_id)

    response = TestClient(app).get(
        "/v1/observability/ping",
        headers={"X-Request-Id": request_id},
    )

    assert response.status_code == 200
    assert response.headers["x-request-id"] == request_id
    assert response.json()["metadata"]["request_id"] == request_id
    assert item is not None
    assert item["history"]["metadata"]["request_id"] == request_id
    assert item["explainability"]["metadata"]["request_id"] == request_id


def test_request_correlation_remains_tenant_isolated_after_restart(tmp_path) -> None:
    provider = DurableHistoryReadProvider.from_directories(
        history_dir=tmp_path / "history",
        explainability_dir=tmp_path / "explainability",
    )

    for tenant_id, request_id in (("alpha", "request-d7-alpha"), ("bravo", "request-d7-bravo")):
        with _request_context(request_id, tenant_id):
            history = ForecastHistoryService().record(
                history_id="shared-history",
                forecast_id=f"forecast-{tenant_id}",
                item_id="ITEM-001",
                location_id="LOC-001",
                model_name="seasonal-naive",
                model_version="1.0",
                forecast_payload={"forecast_quantity": 12.0},
            )
            explanation = HistoricalExplainabilityArchiveService().archive_output(
                archive_id="shared-archive",
                history_id=history.history_id,
                forecast_id=history.forecast_id,
                output=_output(),
            )
            provider.history_store.append(history)
            provider.explainability_store.append(explanation)

    for tenant_id, request_id in (("alpha", "request-d7-alpha"), ("bravo", "request-d7-bravo")):
        with _request_context("read-request", tenant_id):
            item = DurableHistoryReadProvider.from_directories(
                history_dir=tmp_path / "history",
                explainability_dir=tmp_path / "explainability",
            ).build_query_service().get("shared-history")

        assert item is not None
        assert item["history"]["metadata"]["request_id"] == request_id
        assert item["explainability"]["metadata"]["request_id"] == request_id
        assert item["advisory_only"] is True
        assert item["read_only"] is True
        assert item["inventory_source_of_truth_preserved"] is True
