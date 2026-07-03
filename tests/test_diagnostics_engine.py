from invyra_forecasting.constants import Environment
from invyra_forecasting.explainability import DiagnosticSeverity, ForecastDiagnosticsEngine
from invyra_forecasting.orchestration import AdvisoryForecastResponse


def _response(**overrides) -> AdvisoryForecastResponse:
    values = {
        "item_id": "ITEM-001",
        "location_id": "LOC-001",
        "environment": Environment.TEST,
        "analysis_window_days": 30,
        "forecast_days": 14,
        "forecast_quantity": 12.5,
        "projected_days_of_cover": 5.0,
        "stockout_risk": "MEDIUM",
        "confidence": 0.91,
        "explanation": ("Forecast is linked to evidence.",),
        "evidence_refs": ("MOV-001", "SNAPSHOT-001"),
        "intelligence_summary": {"signal_count": 2, "evidence_link_count": 2},
        "model_metadata": {"model_name": "baseline_explainable_demand_model"},
        "advisory_only": True,
        "inventory_source_of_truth_preserved": True,
    }
    values.update(overrides)
    return AdvisoryForecastResponse(**values)


def test_diagnostics_engine_reports_linked_evidence_info():
    report = ForecastDiagnosticsEngine().analyze(_response())

    assert report.item_id == "ITEM-001"
    assert report.has_warnings is False
    assert report.findings[0].code == "EVIDENCE_LINKED"
    assert report.findings[0].severity == DiagnosticSeverity.INFO
    assert report.findings[0].evidence_refs == ("MOV-001", "SNAPSHOT-001")


def test_diagnostics_engine_flags_no_signals_and_unknown_coverage():
    report = ForecastDiagnosticsEngine().analyze(
        _response(
            forecast_quantity=0,
            projected_days_of_cover=None,
            stockout_risk="UNKNOWN",
            confidence=0,
            evidence_refs=(),
            intelligence_summary={"signal_count": 0, "evidence_link_count": 0},
        )
    )

    codes = {finding.code for finding in report.findings}
    assert "NO_SIGNALS" in codes
    assert "COVERAGE_UNKNOWN" in codes
    assert "NO_CONFIDENCE" in codes
    assert "UNKNOWN_STOCKOUT_RISK" in codes
    assert report.has_warnings is True


def test_diagnostics_engine_flags_partial_evidence_and_low_coverage():
    report = ForecastDiagnosticsEngine().analyze(
        _response(
            projected_days_of_cover=2.5,
            confidence=0.45,
            intelligence_summary={"signal_count": 3, "evidence_link_count": 1},
            evidence_refs=("MOV-001",),
        )
    )

    codes = {finding.code for finding in report.findings}
    assert "PARTIAL_EVIDENCE_REFS" in codes
    assert "LOW_COVERAGE" in codes
    assert "LOW_CONFIDENCE" in codes
    assert report.has_warnings is True


def test_diagnostics_engine_flags_high_stockout_risk():
    report = ForecastDiagnosticsEngine().analyze(_response(stockout_risk="HIGH"))

    high_risk = [finding for finding in report.findings if finding.code == "HIGH_STOCKOUT_RISK"]
    assert len(high_risk) == 1
    assert high_risk[0].severity == DiagnosticSeverity.WARNING


def test_diagnostics_engine_flags_guardrail_drift():
    report = ForecastDiagnosticsEngine().analyze(
        _response(
            advisory_only=False,
            inventory_source_of_truth_preserved=False,
        )
    )

    codes = {finding.code for finding in report.findings}
    assert "ADVISORY_GUARDRAIL_MISSING" in codes
    assert "SOURCE_OF_TRUTH_GUARDRAIL_MISSING" in codes
    assert any(finding.severity == DiagnosticSeverity.CRITICAL for finding in report.findings)
