from __future__ import annotations

import pytest

from invyra_forecasting.evaluation_linkage import ForecastEvaluationLink
from invyra_forecasting.evaluation_window import EvaluationWindowService, EvaluationWindowStatus
from invyra_forecasting.history import ForecastHistoryRecord


def _history() -> ForecastHistoryRecord:
    return ForecastHistoryRecord(
        history_id="history-1",
        forecast_id="forecast-1",
        item_id="item-1",
        location_id="location-1",
        model_name="baseline",
        model_version="1.0",
        forecast_payload={"forecast_quantity": 10.0},
        created_at_utc="2026-07-01T00:00:00+00:00",
    )


def _link() -> ForecastEvaluationLink:
    return ForecastEvaluationLink(
        link_id="link-1",
        evaluation_id="evaluation-1",
        history_id="history-1",
        forecast_id="forecast-1",
        snapshot_id=None,
        item_id="item-1",
        location_id="location-1",
        model_name="baseline",
        model_version="1.0",
        forecast_horizon_days=7,
        history_version_number=1,
    )


def test_before_horizon_with_no_actuals_is_not_yet_evaluable() -> None:
    assessment = EvaluationWindowService().assess(
        _history(), _link(), assessed_at_utc="2026-07-04T00:00:00+00:00", actual_data_completeness=0.0
    )
    assert assessment.status is EvaluationWindowStatus.NOT_YET_EVALUABLE
    assert assessment.final_evaluation_eligible is False


def test_open_horizon_with_actuals_is_partially_evaluable() -> None:
    assessment = EvaluationWindowService().assess(
        _history(), _link(), assessed_at_utc="2026-07-04T00:00:00+00:00", actual_data_completeness=0.4
    )
    assert assessment.status is EvaluationWindowStatus.PARTIALLY_EVALUABLE
    assert assessment.final_evaluation_eligible is False


def test_closed_horizon_with_incomplete_actuals_is_insufficient() -> None:
    assessment = EvaluationWindowService().assess(
        _history(), _link(), assessed_at_utc="2026-07-09T00:00:00+00:00", actual_data_completeness=0.9
    )
    assert assessment.status is EvaluationWindowStatus.INSUFFICIENT_ACTUAL_DATA
    assert assessment.final_evaluation_eligible is False


def test_closed_horizon_with_complete_actuals_is_fully_evaluable() -> None:
    assessment = EvaluationWindowService().assess(
        _history(), _link(), assessed_at_utc="2026-07-08T00:00:00+00:00", actual_data_completeness=1.0
    )
    assert assessment.status is EvaluationWindowStatus.FULLY_EVALUABLE
    assert assessment.final_evaluation_eligible is True
    assert assessment.forecast_horizon_end_utc == "2026-07-08T00:00:00+00:00"


def test_completed_evaluation_is_classified_as_evaluated() -> None:
    assessment = EvaluationWindowService().assess(
        _history(),
        _link(),
        assessed_at_utc="2026-07-09T00:00:00+00:00",
        actual_data_completeness=1.0,
        evaluation_completed=True,
    )
    assert assessment.status is EvaluationWindowStatus.EVALUATED
    assert assessment.final_evaluation_eligible is True


def test_requires_timezone_aware_timestamps_and_valid_completeness() -> None:
    with pytest.raises(ValueError, match="UTC offset"):
        EvaluationWindowService().assess(
            _history(), _link(), assessed_at_utc="2026-07-09T00:00:00", actual_data_completeness=1.0
        )
    with pytest.raises(ValueError, match="between 0.0 and 1.0"):
        EvaluationWindowService().assess(
            _history(), _link(), assessed_at_utc="2026-07-09T00:00:00+00:00", actual_data_completeness=1.1
        )


def test_rejects_mismatched_link_and_preserves_guardrails() -> None:
    mismatched = ForecastEvaluationLink(
        **{**_link().to_dict(), "history_id": "other-history"}
    )
    with pytest.raises(ValueError, match="history_id must match"):
        EvaluationWindowService().assess(
            _history(), mismatched, assessed_at_utc="2026-07-09T00:00:00+00:00", actual_data_completeness=1.0
        )

    payload = EvaluationWindowService().assess(
        _history(), _link(), assessed_at_utc="2026-07-09T00:00:00+00:00", actual_data_completeness=1.0
    ).to_dict()
    assert payload["advisory_only"] is True
    assert payload["read_only"] is True
    assert payload["inventory_source_of_truth_preserved"] is True
