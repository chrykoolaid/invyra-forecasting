from __future__ import annotations

from invyra_forecasting.constants import Environment
from invyra_forecasting.decision_gates import ForecastDecisionGateEvaluator
from invyra_forecasting.decision_review import ForecastDecisionReviewPacketBuilder
from invyra_forecasting.models.contracts import ForecastModelOutput


def _forecast(*, confidence: float = 0.80, evidence_refs: tuple[str, ...] = ("evidence::1",)) -> ForecastModelOutput:
    return ForecastModelOutput(
        item_id="item-1",
        location_id="store-1",
        environment=Environment.TEST,
        forecast_days=30,
        forecast_quantity=100.0,
        projected_days_of_cover=10.0,
        stockout_risk="LOW",
        confidence=confidence,
        explanation=("test forecast",),
        evidence_refs=evidence_refs,
        model_name="test_model",
        model_version="8B.test",
    )


def test_decision_review_packet_wraps_ready_forecast_and_gate_result() -> None:
    forecast = _forecast()
    gate = ForecastDecisionGateEvaluator().evaluate(forecast)

    packet = ForecastDecisionReviewPacketBuilder().build(forecast=forecast, decision_gate=gate)

    assert packet.decision_ready is True
    assert packet.forecast.item_id == "item-1"
    assert packet.decision_gate.decision_ready is True
    assert packet.evidence_summary[0] == "Forecast includes 1 evidence reference(s)."


def test_decision_review_packet_preserves_not_ready_gate_state() -> None:
    forecast = _forecast(confidence=0.20)
    gate = ForecastDecisionGateEvaluator().evaluate(forecast)

    packet = ForecastDecisionReviewPacketBuilder().build(forecast=forecast, decision_gate=gate)

    assert packet.decision_ready is False
    assert packet.decision_gate.warnings


def test_decision_review_packet_serializes_governance_metadata() -> None:
    forecast = _forecast()
    gate = ForecastDecisionGateEvaluator().evaluate(forecast)

    packet = ForecastDecisionReviewPacketBuilder().build(forecast=forecast, decision_gate=gate)
    payload = packet.to_dict()

    assert payload["advisory_only"] is True
    assert payload["read_only"] is True
    assert payload["inventory_source_of_truth_preserved"] is True
    assert any("did not mutate inventory" in note for note in payload["review_notes"])


def test_decision_review_packet_summarizes_missing_evidence_refs() -> None:
    forecast = _forecast(evidence_refs=())
    gate = ForecastDecisionGateEvaluator().evaluate(forecast)

    packet = ForecastDecisionReviewPacketBuilder().build(forecast=forecast, decision_gate=gate)

    assert packet.evidence_summary == ("No evidence references were attached to this forecast.",)
