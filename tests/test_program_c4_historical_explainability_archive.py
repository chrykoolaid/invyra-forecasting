from __future__ import annotations

from contextlib import contextmanager
from dataclasses import FrozenInstanceError

import pytest

from invyra_forecasting.api import tenant_context
from invyra_forecasting.constants import Environment
from invyra_forecasting.explainability_archive import (
    HistoricalExplainabilityArchiveService,
    InMemoryHistoricalExplainabilityRepository,
)
from invyra_forecasting.models.contracts import ForecastModelOutput


@contextmanager
def _tenant(tenant_id: str | None):
    token = tenant_context._TENANT_ID.set(tenant_context.normalize_tenant_id(tenant_id))
    try:
        yield
    finally:
        tenant_context._TENANT_ID.reset(token)


def _output(*, quantity: float = 12.0, confidence: float = 0.82) -> ForecastModelOutput:
    return ForecastModelOutput(
        item_id="ITEM-001",
        location_id="LOC-001",
        environment=Environment.TEST,
        forecast_days=7,
        forecast_quantity=quantity,
        projected_days_of_cover=4.5,
        stockout_risk="MEDIUM",
        confidence=confidence,
        explanation=("Demand trend increased.", "Seasonality remained stable."),
        evidence_refs=("evidence-1", "evidence-2"),
        model_name="seasonal-naive",
        model_version="1.2",
    )


def test_archive_preserves_generated_output_exactly():
    service = HistoricalExplainabilityArchiveService()
    output = _output()

    archived = service.archive_output(
        archive_id="archive-1",
        history_id="history-1",
        forecast_id="forecast-1",
        output=output,
        reasoning_summary=("Selected for stable seasonal demand.",),
        supporting_metrics={"mae": 1.25, "coverage_days": 4.5},
    )

    assert archived.model_name == output.model_name
    assert archived.model_version == output.model_version
    assert archived.confidence == output.confidence
    assert archived.explanation == output.explanation
    assert archived.evidence_refs == output.evidence_refs
    assert archived.reasoning_summary == ("Selected for stable seasonal demand.",)
    assert archived.supporting_metrics == {"mae": 1.25, "coverage_days": 4.5}


def test_archive_record_is_immutable_and_read_only():
    archived = HistoricalExplainabilityArchiveService().archive_output(
        archive_id="archive-1",
        history_id="history-1",
        forecast_id="forecast-1",
        output=_output(),
    )

    with pytest.raises(FrozenInstanceError):
        archived.confidence = 0.1

    assert archived.advisory_only is True
    assert archived.read_only is True
    assert archived.inventory_source_of_truth_preserved is True


def test_history_can_only_be_archived_once_per_namespace():
    service = HistoricalExplainabilityArchiveService()
    service.archive_output(
        archive_id="archive-1",
        history_id="history-1",
        forecast_id="forecast-1",
        output=_output(),
    )

    with pytest.raises(
        ValueError,
        match="history record already has explainability archived: history-1",
    ):
        service.archive_output(
            archive_id="archive-2",
            history_id="history-1",
            forecast_id="forecast-1",
            output=_output(quantity=13.0),
        )


def test_archive_is_tenant_isolated():
    repository = InMemoryHistoricalExplainabilityRepository()
    service = HistoricalExplainabilityArchiveService(repository)

    with _tenant("alpha"):
        alpha = service.archive_output(
            archive_id="shared-id",
            history_id="shared-history",
            forecast_id="forecast-1",
            output=_output(confidence=0.9),
        )

    with _tenant("bravo"):
        bravo = service.archive_output(
            archive_id="shared-id",
            history_id="shared-history",
            forecast_id="forecast-1",
            output=_output(confidence=0.4),
        )

    with _tenant("alpha"):
        assert service.get("shared-id") == alpha
        assert service.for_history("shared-history").confidence == 0.9

    with _tenant("bravo"):
        assert service.get("shared-id") == bravo
        assert service.for_history("shared-history").confidence == 0.4


def test_forecast_archive_timeline_is_read_only_and_ordered():
    service = HistoricalExplainabilityArchiveService()
    first = service.archive_output(
        archive_id="archive-1",
        history_id="history-1",
        forecast_id="forecast-1",
        output=_output(confidence=0.7),
    )
    second = service.archive_output(
        archive_id="archive-2",
        history_id="history-2",
        forecast_id="forecast-1",
        output=_output(confidence=0.8),
    )

    assert service.for_forecast("forecast-1") == (first, second)
    assert service.for_forecast("missing") == ()


def test_serialization_preserves_archived_collections():
    archived = HistoricalExplainabilityArchiveService().archive_output(
        archive_id="archive-1",
        history_id="history-1",
        forecast_id="forecast-1",
        output=_output(),
        reasoning_summary=("reason-1",),
        supporting_metrics={"metric": 1.0},
    )

    payload = archived.to_dict()

    assert payload["explanation"] == ["Demand trend increased.", "Seasonality remained stable."]
    assert payload["evidence_refs"] == ["evidence-1", "evidence-2"]
    assert payload["reasoning_summary"] == ["reason-1"]
    assert payload["supporting_metrics"] == {"metric": 1.0}
