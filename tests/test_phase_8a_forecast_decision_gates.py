from __future__ import annotations

from invyra_forecasting.constants import Environment
from invyra_forecasting.decision_gates import ForecastDecisionGateConfiguration, ForecastDecisionGateEvaluator
from invyra_forecasting.models.contracts import ForecastModelOutput


def _output(
    *,
    confidence: float = 0.80,
    evidence_refs: tuple[str, ...] = ("evidence::forecast",),
    stockout_risk: str = "LOW",
    advisory_only: bool = True,
    source_of_truth: bool = True,
) -> ForecastModelOutput:
    return ForecastModelOutput(
        item_id="item-1",
        location_id="store-1",
        environment=Environment.TEST,
        forecast_days=30,
        forecast_quantity=100.0,
        projected_days_of_cover=10.0,
        stockout_risk=stockout_risk,
        confidence=confidence,
        explanation=("test forecast",),
        evidence_refs=evidence_refs,
        advisory_only=advisory_only,
        inventory_source_of_truth_preserved=source_of_truth,
        model_name="test_model",
        model_version="8A.test",
    )


def test_decision_gate_marks_evidence_backed_forecast_ready() -> None:
    evaluator = ForecastDecisionGateEvaluator()

    result = evaluator.evaluate(_output())

    assert result.decision_ready is True
    assert result.warnings == ()
    assert any("advisory-only" in reason for reason in result.reasons)
    assert any("did not mutate inventory" in reason for reason in result.reasons)


def test_decision_gate_flags_low_confidence_forecast() -> None:
    evaluator = ForecastDecisionGateEvaluator()

    result = evaluator.evaluate(_output(confidence=0.30))
    payload = result.to_dict()

    assert result.decision_ready is False
    assert any("below minimum" in warning for warning in result.warnings)
    assert payload["advisory_only"] is True
    assert payload["read_only"] is True
    assert payload["inventory_source_of_truth_preserved"] is True


def test_decision_gate_flags_forecast_without_evidence_refs() -> None:
    evaluator = ForecastDecisionGateEvaluator()

    result = evaluator.evaluate(_output(evidence_refs=()))

    assert result.decision_ready is False
    assert any("evidence reference" in warning for warning in result.warnings)


def test_decision_gate_requires_extra_confidence_for_critical_stockout_risk() -> None:
    evaluator = ForecastDecisionGateEvaluator()

    result = evaluator.evaluate(_output(stockout_risk="CRITICAL", confidence=0.60))

    assert result.decision_ready is False
    assert any("Critical stockout risk" in warning for warning in result.warnings)


def test_decision_gate_configuration_is_versioned_and_serialized() -> None:
    config = ForecastDecisionGateConfiguration(
        version="8A.test",
        minimum_confidence=0.75,
        minimum_evidence_refs=2,
        critical_risk_requires_high_confidence=0.85,
    )
    evaluator = ForecastDecisionGateEvaluator(config)

    result = evaluator.evaluate(_output(confidence=0.80, evidence_refs=("evidence::1", "evidence::2")))
    payload = result.to_dict()

    assert result.decision_ready is True
    assert payload["configuration"]["version"] == "8A.test"
    assert payload["configuration"]["minimum_confidence"] == 0.75
