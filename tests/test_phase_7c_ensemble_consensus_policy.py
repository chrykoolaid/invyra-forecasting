from __future__ import annotations

from invyra_forecasting.constants import Environment
from invyra_forecasting.models import (
    EnsembleConsensusConfiguration,
    EnsembleConsensusPolicy,
    EnsembleMemberForecast,
    WeightedAverageEnsembleForecaster,
)
from invyra_forecasting.models.contracts import ForecastModelOutput


def _output(*, model_name: str, quantity: float, confidence: float) -> ForecastModelOutput:
    return ForecastModelOutput(
        item_id="item-1",
        location_id="store-1",
        environment=Environment.TEST,
        forecast_days=30,
        forecast_quantity=quantity,
        projected_days_of_cover=10.0,
        stockout_risk="LOW",
        confidence=confidence,
        explanation=(f"{model_name} advisory forecast",),
        evidence_refs=(f"evidence::{model_name}",),
        model_name=model_name,
        model_version="test",
    )


def test_ensemble_consensus_policy_passes_when_members_agree() -> None:
    forecaster = WeightedAverageEnsembleForecaster(consensus_policy=EnsembleConsensusPolicy())

    result = forecaster.combine(
        (
            EnsembleMemberForecast("model-a", _output(model_name="model-a", quantity=100.0, confidence=0.80), 1.0),
            EnsembleMemberForecast("model-b", _output(model_name="model-b", quantity=110.0, confidence=0.82), 1.0),
        )
    )

    assert result.consensus_assessment is not None
    assert result.consensus_assessment.consensus_passed is True
    assert result.consensus_assessment.warnings == ()
    assert result.consensus_assessment.average_confidence == 0.81
    assert result.consensus_assessment.quantity_spread_ratio == 0.095238


def test_ensemble_consensus_policy_warns_on_sparse_low_confidence_disagreement() -> None:
    config = EnsembleConsensusConfiguration(
        minimum_member_count=3,
        minimum_confidence=0.75,
        maximum_quantity_spread_ratio=0.20,
    )
    forecaster = WeightedAverageEnsembleForecaster(consensus_policy=EnsembleConsensusPolicy(config))

    result = forecaster.combine(
        (
            EnsembleMemberForecast("model-a", _output(model_name="model-a", quantity=50.0, confidence=0.60), 1.0),
            EnsembleMemberForecast("model-b", _output(model_name="model-b", quantity=100.0, confidence=0.62), 1.0),
        )
    )

    assert result.consensus_assessment is not None
    assert result.consensus_assessment.consensus_passed is False
    assert len(result.consensus_assessment.warnings) == 3
    assert any("minimum required" in warning for warning in result.consensus_assessment.warnings)
    assert any("below minimum" in warning for warning in result.consensus_assessment.warnings)
    assert any("exceeds maximum" in warning for warning in result.consensus_assessment.warnings)


def test_ensemble_consensus_assessment_preserves_read_only_governance() -> None:
    forecaster = WeightedAverageEnsembleForecaster(consensus_policy=EnsembleConsensusPolicy())

    result = forecaster.combine(
        (
            EnsembleMemberForecast("model-a", _output(model_name="model-a", quantity=90.0, confidence=0.90), 1.0),
            EnsembleMemberForecast("model-b", _output(model_name="model-b", quantity=95.0, confidence=0.88), 1.0),
        )
    )
    assert result.consensus_assessment is not None
    payload = result.consensus_assessment.to_dict()

    assert payload["advisory_only"] is True
    assert payload["read_only"] is True
    assert payload["inventory_source_of_truth_preserved"] is True
    assert payload["configuration"]["version"] == "7C.1"


def test_ensemble_without_policy_remains_backward_compatible() -> None:
    forecaster = WeightedAverageEnsembleForecaster()

    result = forecaster.combine(
        (
            EnsembleMemberForecast("model-a", _output(model_name="model-a", quantity=90.0, confidence=0.90), 1.0),
            EnsembleMemberForecast("model-b", _output(model_name="model-b", quantity=95.0, confidence=0.88), 1.0),
        )
    )

    assert result.consensus_assessment is None
    assert result.output.forecast_quantity == 92.5
