from __future__ import annotations

from contextlib import contextmanager

import pytest

from invyra_forecasting.api import tenant_context
from invyra_forecasting.evaluation import (
    EvaluationPersistenceService,
    ForecastEvaluationService,
    ForecastOutcome,
    ForecastPrediction,
)
from invyra_forecasting.evaluation_linkage import ForecastEvaluationLinkageService
from invyra_forecasting.history import ForecastHistoryRecord


@contextmanager
def _tenant(tenant_id: str | None):
    token = tenant_context._TENANT_ID.set(tenant_context.normalize_tenant_id(tenant_id))
    try:
        yield
    finally:
        tenant_context._TENANT_ID.reset(token)


def _history(**overrides) -> ForecastHistoryRecord:
    values = {
        "history_id": "history-e1",
        "forecast_id": "forecast-e1",
        "item_id": "ITEM-001",
        "location_id": "LOC-001",
        "model_name": "seasonal-naive",
        "model_version": "1.0",
        "forecast_payload": {"forecast_quantity": 12.0},
        "snapshot_id": "snapshot-e1",
    }
    values.update(overrides)
    return ForecastHistoryRecord(**values)


def _evaluation(**prediction_overrides):
    prediction_values = {
        "forecast_id": "forecast-e1",
        "item_id": "ITEM-001",
        "location_id": "LOC-001",
        "model_name": "seasonal-naive",
        "model_version": "1.0",
        "forecast_horizon_days": 7,
        "predicted_quantity": 12.0,
        "confidence": 0.8,
    }
    prediction_values.update(prediction_overrides)
    result = ForecastEvaluationService().evaluate(
        ForecastPrediction(**prediction_values),
        ForecastOutcome(
            forecast_id=prediction_values["forecast_id"],
            actual_quantity=10.0,
        ),
    )
    return EvaluationPersistenceService().persist(
        result,
        evaluation_id="evaluation-e1",
        snapshot_id="snapshot-e1",
    )


def test_e1_links_matching_history_and_evaluation_identity() -> None:
    service = ForecastEvaluationLinkageService()

    link = service.link(_history(), _evaluation())

    assert link.link_id == "evaluation-e1"
    assert link.evaluation_id == "evaluation-e1"
    assert link.history_id == "history-e1"
    assert link.forecast_id == "forecast-e1"
    assert link.snapshot_id == "snapshot-e1"
    assert link.forecast_horizon_days == 7
    assert link.history_version_number == 1
    assert service.for_evaluation("evaluation-e1") == link
    assert service.for_history("history-e1") == (link,)


def test_e1_rejects_mismatched_forecast_identity() -> None:
    service = ForecastEvaluationLinkageService()

    with pytest.raises(ValueError, match="forecast_id must match"):
        service.link(_history(forecast_id="different-forecast"), _evaluation())


@pytest.mark.parametrize(
    ("history_override", "prediction_override", "message"),
    [
        ({"item_id": "ITEM-OTHER"}, {}, "item_id must match"),
        ({"location_id": "LOC-OTHER"}, {}, "location_id must match"),
        ({"model_name": "other-model"}, {}, "model_name must match"),
        ({"model_version": "2.0"}, {}, "model_version must match"),
    ],
)
def test_e1_rejects_mismatched_history_dimensions(
    history_override,
    prediction_override,
    message,
) -> None:
    service = ForecastEvaluationLinkageService()

    with pytest.raises(ValueError, match=message):
        service.link(_history(**history_override), _evaluation(**prediction_override))


def test_e1_rejects_conflicting_snapshot_identity() -> None:
    service = ForecastEvaluationLinkageService()

    with pytest.raises(ValueError, match="snapshot_id must match"):
        service.link(_history(snapshot_id="history-snapshot"), _evaluation())


def test_e1_rejects_duplicate_evaluation_linkage() -> None:
    service = ForecastEvaluationLinkageService()
    history = _history()
    evaluation = _evaluation()
    service.link(history, evaluation, link_id="link-one")

    with pytest.raises(ValueError, match="evaluation already linked"):
        service.link(history, evaluation, link_id="link-two")


def test_e1_link_repository_is_tenant_isolated() -> None:
    service = ForecastEvaluationLinkageService()

    with _tenant("alpha"):
        alpha = service.link(_history(), _evaluation(), link_id="shared-link")
        assert service.get("shared-link") == alpha

    with _tenant("bravo"):
        assert service.get("shared-link") is None
        bravo = service.link(_history(), _evaluation(), link_id="shared-link")
        assert service.get("shared-link") == bravo

    with _tenant("alpha"):
        assert service.get("shared-link") == alpha


def test_e1_serialization_and_enterprise_guardrails() -> None:
    link = ForecastEvaluationLinkageService().link(_history(), _evaluation())
    payload = link.to_dict()

    assert payload["evaluation_id"] == "evaluation-e1"
    assert payload["history_id"] == "history-e1"
    assert payload["advisory_only"] is True
    assert payload["read_only"] is True
    assert payload["inventory_source_of_truth_preserved"] is True
