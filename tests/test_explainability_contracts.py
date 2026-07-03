from invyra_forecasting.constants import Environment
from invyra_forecasting.explainability import (
    ConfidenceBreakdown,
    DiagnosticFinding,
    DiagnosticReport,
    DiagnosticSeverity,
    EvidenceSummary,
    ForecastExplanation,
    RecommendationNarrative,
)


def test_evidence_summary_serializes_environment_and_refs():
    summary = EvidenceSummary(
        item_id="ITEM-001",
        location_id="LOC-001",
        environment=Environment.TEST,
        sales_signal_count=12,
        gap_scan_signal_count=2,
        evidence_ref_count=2,
        evidence_refs=("MOV-001", "GAP-001"),
        freshness_notes=("Inventory snapshot is recent.",),
    )

    payload = summary.to_dict()

    assert payload["environment"] == "TEST"
    assert payload["sales_signal_count"] == 12
    assert payload["gap_scan_signal_count"] == 2
    assert payload["evidence_refs"] == ["MOV-001", "GAP-001"]
    assert payload["freshness_notes"] == ["Inventory snapshot is recent."]


def test_diagnostic_report_flags_warnings():
    report = DiagnosticReport(
        item_id="ITEM-001",
        location_id="LOC-001",
        environment=Environment.TEST,
        findings=(
            DiagnosticFinding(
                code="STALE_GAP_SCAN",
                severity=DiagnosticSeverity.WARNING,
                message="Gap Scan evidence is older than 14 days.",
                confidence_impact=-0.05,
                evidence_refs=("GAP-001",),
            ),
        ),
    )

    payload = report.to_dict()

    assert report.has_warnings is True
    assert payload["has_warnings"] is True
    assert payload["findings"][0]["severity"] == "WARNING"
    assert payload["findings"][0]["evidence_refs"] == ["GAP-001"]


def test_forecast_explanation_preserves_governance_fields():
    evidence = EvidenceSummary(
        item_id="ITEM-001",
        location_id="LOC-001",
        environment=Environment.TEST,
        sales_signal_count=10,
        evidence_ref_count=1,
        evidence_refs=("MOV-001",),
    )
    confidence = ConfidenceBreakdown(
        overall=0.91,
        signal_quality=0.96,
        evidence_completeness=0.94,
        history_quality=0.9,
        data_freshness=0.95,
        coverage_quality=0.87,
        notes=("Recent sales history is complete.",),
    )
    diagnostics = DiagnosticReport(
        item_id="ITEM-001",
        location_id="LOC-001",
        environment=Environment.TEST,
    )
    narrative = RecommendationNarrative(
        summary="Demand is increasing while available stock is projected to cover only five days.",
        reasoning=("Recent sales activity supports the forecast.",),
        assumptions=("Inventory snapshot is current.",),
    )

    explanation = ForecastExplanation(
        item_id="ITEM-001",
        location_id="LOC-001",
        environment=Environment.TEST,
        forecast_quantity=14.5,
        forecast_days=14,
        stockout_risk="MEDIUM",
        explanation_lines=("Average daily demand is rising.",),
        evidence_summary=evidence,
        confidence_breakdown=confidence,
        diagnostic_report=diagnostics,
        narrative=narrative,
        audit_refs=("MOV-001",),
    )

    payload = explanation.to_dict()

    assert payload["environment"] == "TEST"
    assert payload["advisory_only"] is True
    assert payload["inventory_source_of_truth_preserved"] is True
    assert payload["audit_refs"] == ["MOV-001"]
    assert payload["confidence_breakdown"]["overall"] == 0.91
    assert payload["narrative"]["summary"].startswith("Demand is increasing")
