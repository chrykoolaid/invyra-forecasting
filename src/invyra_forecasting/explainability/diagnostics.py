from __future__ import annotations

from invyra_forecasting.explainability.objects import (
    DiagnosticFinding,
    DiagnosticReport,
    DiagnosticSeverity,
)
from invyra_forecasting.orchestration.contracts import AdvisoryForecastResponse


class ForecastDiagnosticsEngine:
    """Detects explainability diagnostics from advisory forecast responses.

    Diagnostics are read-only advisory findings. They do not mutate inventory,
    create stock movements, create purchase orders, approve purchase orders, or
    replace the inventory ledger.
    """

    def analyze(self, response: AdvisoryForecastResponse) -> DiagnosticReport:
        findings: list[DiagnosticFinding] = []
        findings.extend(self._check_sparse_evidence(response))
        findings.extend(self._check_missing_coverage(response))
        findings.extend(self._check_low_confidence(response))
        findings.extend(self._check_stockout_risk(response))
        findings.extend(self._check_guardrails(response))

        return DiagnosticReport(
            item_id=response.item_id,
            location_id=response.location_id,
            environment=response.environment,
            findings=tuple(findings),
        )

    def _check_sparse_evidence(self, response: AdvisoryForecastResponse) -> list[DiagnosticFinding]:
        signal_count = int(response.intelligence_summary.get("signal_count", 0))
        evidence_count = int(response.intelligence_summary.get("evidence_link_count", len(response.evidence_refs)))

        if signal_count == 0:
            return [
                DiagnosticFinding(
                    code="NO_SIGNALS",
                    severity=DiagnosticSeverity.WARNING,
                    message="No forecasting signals were available for this item/location.",
                    confidence_impact=-0.25,
                )
            ]
        if evidence_count == 0:
            return [
                DiagnosticFinding(
                    code="NO_EVIDENCE_REFS",
                    severity=DiagnosticSeverity.WARNING,
                    message="Forecast signals were present but no evidence references were available.",
                    confidence_impact=-0.2,
                )
            ]
        if evidence_count < signal_count:
            return [
                DiagnosticFinding(
                    code="PARTIAL_EVIDENCE_REFS",
                    severity=DiagnosticSeverity.NOTICE,
                    message="Some forecast signals do not have evidence references.",
                    confidence_impact=-0.05,
                    evidence_refs=response.evidence_refs,
                )
            ]
        return [
            DiagnosticFinding(
                code="EVIDENCE_LINKED",
                severity=DiagnosticSeverity.INFO,
                message="Forecast evidence references are available.",
                confidence_impact=0.0,
                evidence_refs=response.evidence_refs,
            )
        ]

    def _check_missing_coverage(self, response: AdvisoryForecastResponse) -> list[DiagnosticFinding]:
        if response.projected_days_of_cover is None:
            return [
                DiagnosticFinding(
                    code="COVERAGE_UNKNOWN",
                    severity=DiagnosticSeverity.NOTICE,
                    message="Projected days of cover is unavailable because stock or demand evidence is incomplete.",
                    confidence_impact=-0.1,
                    evidence_refs=response.evidence_refs,
                )
            ]
        if response.projected_days_of_cover <= 3:
            return [
                DiagnosticFinding(
                    code="LOW_COVERAGE",
                    severity=DiagnosticSeverity.WARNING,
                    message="Projected days of cover is very low.",
                    confidence_impact=0.0,
                    evidence_refs=response.evidence_refs,
                )
            ]
        return []

    def _check_low_confidence(self, response: AdvisoryForecastResponse) -> list[DiagnosticFinding]:
        if response.confidence <= 0:
            return [
                DiagnosticFinding(
                    code="NO_CONFIDENCE",
                    severity=DiagnosticSeverity.WARNING,
                    message="Forecast confidence is zero.",
                    confidence_impact=-0.25,
                    evidence_refs=response.evidence_refs,
                )
            ]
        if response.confidence < 0.5:
            return [
                DiagnosticFinding(
                    code="LOW_CONFIDENCE",
                    severity=DiagnosticSeverity.NOTICE,
                    message="Forecast confidence is below the recommended review threshold.",
                    confidence_impact=-0.1,
                    evidence_refs=response.evidence_refs,
                )
            ]
        return []

    def _check_stockout_risk(self, response: AdvisoryForecastResponse) -> list[DiagnosticFinding]:
        if response.stockout_risk == "HIGH":
            return [
                DiagnosticFinding(
                    code="HIGH_STOCKOUT_RISK",
                    severity=DiagnosticSeverity.WARNING,
                    message="Stockout risk is high and should be reviewed promptly.",
                    confidence_impact=0.0,
                    evidence_refs=response.evidence_refs,
                )
            ]
        if response.stockout_risk == "UNKNOWN":
            return [
                DiagnosticFinding(
                    code="UNKNOWN_STOCKOUT_RISK",
                    severity=DiagnosticSeverity.NOTICE,
                    message="Stockout risk is unknown because evidence is incomplete.",
                    confidence_impact=-0.1,
                    evidence_refs=response.evidence_refs,
                )
            ]
        return []

    def _check_guardrails(self, response: AdvisoryForecastResponse) -> list[DiagnosticFinding]:
        findings: list[DiagnosticFinding] = []
        if response.advisory_only is not True:
            findings.append(
                DiagnosticFinding(
                    code="ADVISORY_GUARDRAIL_MISSING",
                    severity=DiagnosticSeverity.CRITICAL,
                    message="Advisory-only guardrail is not preserved on the forecast response.",
                    confidence_impact=-1.0,
                )
            )
        if response.inventory_source_of_truth_preserved is not True:
            findings.append(
                DiagnosticFinding(
                    code="SOURCE_OF_TRUTH_GUARDRAIL_MISSING",
                    severity=DiagnosticSeverity.CRITICAL,
                    message="Inventory source-of-truth guardrail is not preserved on the forecast response.",
                    confidence_impact=-1.0,
                )
            )
        return findings
