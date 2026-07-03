from invyra_forecasting.constants import Environment
from invyra_forecasting.explainability import ForecastExplanationBuilder
from invyra_forecasting.orchestration import AdvisoryForecastResponse


def _response_with_evidence() -> AdvisoryForecastResponse:
    return AdvisoryForecastResponse(
        item_id="ITEM-001",
        location_id="LOC-001",
        environment=Environment.TEST,
        analysis_window_days=30,
        forecast_days=14,
        forecast_quantity=12.5,
        projected_days_of_cover=5.0,
        stockout_risk="MEDIUM",
        confidence=0.91,
        explanation=(
            "Average daily demand from intelligence features is 0.8929 units.",
            "Forecast is linked to 2 evidence reference(s).",
        ),
        evidence_refs=("MOV-001", "SNAPSHOT-001"),
        intelligence_summary={
            "signal_count": 2,
            "weighted_signal_count": 1.7,
            "quality_assessment_count": 2,
            "evidence_link_count": 2,
            "pipeline_phase": "2V",
        },
        model_metadata={
            "model_name": "baseline_explainable_demand_model",
            "model_version": "2W.1",
            "advisory_only": True,
            "inventory_source_of_truth_preserved": True,
        },
    )


def test_builder_creates_forecast_explanation_from_advisory_response():
    explanation = ForecastExplanationBuilder().build(_response_with_evidence())

    assert explanation.item_id == "ITEM-001"
    assert explanation.location_id == "LOC-001"
    assert explanation.environment == Environment.TEST
    assert explanation.forecast_quantity == 12.5
    assert explanation.forecast_days == 14
    assert explanation.stockout_risk == "MEDIUM"
    assert explanation.evidence_summary.evidence_ref_count == 2
    assert explanation.evidence_summary.evidence_refs == ("MOV-001", "SNAPSHOT-001")
    assert explanation.confidence_breakdown.overall == 0.91
    assert explanation.confidence_breakdown.evidence_completeness == 1.0
    assert explanation.narrative.summary.startswith("Stockout risk is moderate")
    assert explanation.audit_refs == ("MOV-001", "SNAPSHOT-001")
    assert explanation.advisory_only is True
    assert explanation.inventory_source_of_truth_preserved is True


def test_builder_serializes_enterprise_explanation_payload():
    payload = ForecastExplanationBuilder().build(_response_with_evidence()).to_dict()

    assert payload["environment"] == "TEST"
    assert payload["evidence_summary"]["evidence_refs"] == ["MOV-001", "SNAPSHOT-001"]
    assert payload["confidence_breakdown"]["overall"] == 0.91
    assert payload["diagnostic_report"]["has_warnings"] is False
    assert payload["narrative"]["assumptions"] == [
        "Inventory remains the source of truth.",
        "Forecast output is advisory and requires manager review before operational action.",
    ]
    assert payload["advisory_only"] is True


def test_builder_flags_no_evidence_in_narrative_warning():
    response = AdvisoryForecastResponse(
        item_id="ITEM-MISSING",
        location_id="LOC-001",
        environment=Environment.TEST,
        analysis_window_days=30,
        forecast_days=14,
        forecast_quantity=0,
        projected_days_of_cover=None,
        stockout_risk="UNKNOWN",
        confidence=0,
        explanation=("Forecast has no evidence references and should be treated with caution.",),
        evidence_refs=(),
        intelligence_summary={"signal_count": 0, "evidence_link_count": 0},
        model_metadata={"model_name": "baseline_explainable_demand_model"},
    )

    explanation = ForecastExplanationBuilder().build(response)

    assert explanation.confidence_breakdown.overall == 0
    assert explanation.confidence_breakdown.evidence_completeness == 0
    assert explanation.confidence_breakdown.coverage_quality == 0
    assert explanation.narrative.warnings == ("Forecast has no evidence references and should be treated with caution.",)
    assert "Projected days of cover is unavailable" in explanation.explanation_lines[4]
