from __future__ import annotations

import pytest

from invyra_forecasting.constants import Environment
from invyra_forecasting.models import EnsembleMemberForecast, WeightedAverageEnsembleForecaster
from invyra_forecasting.models.contracts import ForecastModelOutput


def _output(
    *,
    model_name: str,
    quantity: float,
    cover: float | None,
    risk: str,
    confidence: float,
    advisory_only: bool = True,
    source_of_truth: bool = True,
) -> ForecastModelOutput:
    return ForecastModelOutput(
        item_id="item-1",
        location_id="store-1",
        environment=Environment.TEST,
        forecast_days=30,
        forecast_quantity=quantity,
        projected_days_of_cover=cover,
        stockout_risk=risk,
        confidence=confidence,
        explanation=(f"{model_name} advisory forecast",),
        evidence_refs=(f"evidence::{model_name}",),
        advisory_only=advisory_only,
        inventory_source_of_truth_preserved=source_of_truth,
        model_name=model_name,
        model_version="test",
    )


def test_weighted_average_ensemble_blends_outputs_with_normalized_weights() -> None:
    forecaster = WeightedAverageEnsembleForecaster()

    result = forecaster.combine(
        (
            EnsembleMemberForecast("model-a", _output(model_name="model-a", quantity=100.0, cover=10.0, risk="LOW", confidence=0.80), 3.0),
            EnsembleMemberForecast("model-b", _output(model_name="model-b", quantity=200.0, cover=20.0, risk="HIGH", confidence=0.60), 1.0),
        )
    )

    assert result.output.forecast_quantity == 125.0
    assert result.output.projected_days_of_cover == 12.5
    assert result.output.confidence == 0.75
    assert result.output.stockout_risk == "HIGH"
    assert result.output.model_name == "ensemble_weighted_average"
    assert result.output.model_version == "7B.1"
    assert result.audit_record.member_weights == {"model-a": 0.75, "model-b": 0.25}


def test_ensemble_audit_preserves_advisory_read_only_governance() -> None:
    forecaster = WeightedAverageEnsembleForecaster()

    result = forecaster.combine(
        (
            EnsembleMemberForecast("model-a", _output(model_name="model-a", quantity=40.0, cover=8.0, risk="MEDIUM", confidence=0.70), 1.0),
            EnsembleMemberForecast("model-b", _output(model_name="model-b", quantity=60.0, cover=12.0, risk="LOW", confidence=0.90), 1.0),
        )
    )
    audit_payload = result.audit_record.to_dict()

    assert result.output.advisory_only is True
    assert result.output.inventory_source_of_truth_preserved is True
    assert audit_payload["advisory_only"] is True
    assert audit_payload["read_only"] is True
    assert audit_payload["inventory_source_of_truth_preserved"] is True
    assert any("did not mutate inventory" in reason for reason in result.explanation)


def test_ensemble_rejects_members_that_break_governance_guardrails() -> None:
    forecaster = WeightedAverageEnsembleForecaster()

    with pytest.raises(ValueError, match="guardrails"):
        forecaster.combine(
            (
                EnsembleMemberForecast(
                    "unsafe-model",
                    _output(
                        model_name="unsafe-model",
                        quantity=50.0,
                        cover=10.0,
                        risk="LOW",
                        confidence=0.70,
                        advisory_only=False,
                    ),
                    1.0,
                ),
            )
        )


def test_ensemble_rejects_mismatched_forecast_scope() -> None:
    forecaster = WeightedAverageEnsembleForecaster()
    mismatched_location = ForecastModelOutput(
        item_id="item-1",
        location_id="store-2",
        environment=Environment.TEST,
        forecast_days=30,
        forecast_quantity=55.0,
        projected_days_of_cover=11.0,
        stockout_risk="LOW",
        confidence=0.80,
        explanation=("mismatched location",),
        evidence_refs=("evidence::mismatch",),
    )

    with pytest.raises(ValueError, match="same item and location"):
        forecaster.combine(
            (
                EnsembleMemberForecast("model-a", _output(model_name="model-a", quantity=50.0, cover=10.0, risk="LOW", confidence=0.70), 1.0),
                EnsembleMemberForecast("model-b", mismatched_location, 1.0),
            )
        )
