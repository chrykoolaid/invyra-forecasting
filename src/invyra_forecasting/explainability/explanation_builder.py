from __future__ import annotations

from invyra_forecasting.explainability.objects import (
    ConfidenceBreakdown,
    DiagnosticReport,
    EvidenceSummary,
    ForecastExplanation,
    RecommendationNarrative,
)
from invyra_forecasting.orchestration.contracts import AdvisoryForecastResponse


class ForecastExplanationBuilder:
    """Builds deterministic enterprise explanations from advisory forecasts.

    The builder is read-only. It does not mutate inventory, create stock
    movements, create purchase orders, approve purchase orders, or replace the
    inventory ledger.
    """

    def build(self, response: AdvisoryForecastResponse) -> ForecastExplanation:
        evidence = self._build_evidence_summary(response)
        confidence = self._build_confidence_breakdown(response)
        diagnostics = DiagnosticReport(
            item_id=response.item_id,
            location_id=response.location_id,
            environment=response.environment,
        )
        narrative = self._build_narrative(response)
        explanation_lines = self._build_explanation_lines(response, evidence, confidence)

        return ForecastExplanation(
            item_id=response.item_id,
            location_id=response.location_id,
            environment=response.environment,
            forecast_quantity=response.forecast_quantity,
            forecast_days=response.forecast_days,
            stockout_risk=response.stockout_risk,
            explanation_lines=tuple(explanation_lines),
            evidence_summary=evidence,
            confidence_breakdown=confidence,
            diagnostic_report=diagnostics,
            narrative=narrative,
            audit_refs=response.evidence_refs,
            advisory_only=True,
            inventory_source_of_truth_preserved=True,
        )

    def _build_evidence_summary(self, response: AdvisoryForecastResponse) -> EvidenceSummary:
        signal_count = int(response.intelligence_summary.get("signal_count", 0))
        evidence_count = int(response.intelligence_summary.get("evidence_link_count", len(response.evidence_refs)))
        freshness_notes: list[str] = []
        if evidence_count == 0:
            freshness_notes.append("No evidence references were available for this forecast.")
        else:
            freshness_notes.append("Forecast evidence references were carried forward from the intelligence pipeline.")

        return EvidenceSummary(
            item_id=response.item_id,
            location_id=response.location_id,
            environment=response.environment,
            sales_signal_count=signal_count,
            evidence_ref_count=evidence_count,
            evidence_refs=response.evidence_refs,
            freshness_notes=tuple(freshness_notes),
        )

    def _build_confidence_breakdown(self, response: AdvisoryForecastResponse) -> ConfidenceBreakdown:
        overall = round(response.confidence, 4)
        evidence_count = int(response.intelligence_summary.get("evidence_link_count", len(response.evidence_refs)))
        signal_count = int(response.intelligence_summary.get("signal_count", 0))
        evidence_completeness = 1.0 if evidence_count and signal_count and evidence_count >= signal_count else max(0.0, min(1.0, evidence_count / max(signal_count, 1)))
        notes: list[str] = ["Overall confidence is inherited from the intelligence pipeline and model handoff layer."]
        if evidence_completeness < 1.0:
            notes.append("Evidence completeness is reduced because not every signal has an evidence reference.")

        return ConfidenceBreakdown(
            overall=overall,
            signal_quality=overall,
            evidence_completeness=round(evidence_completeness, 4),
            history_quality=overall if signal_count else 0.0,
            data_freshness=overall if evidence_count else 0.0,
            coverage_quality=overall if response.projected_days_of_cover is not None else 0.0,
            notes=tuple(notes),
        )

    def _build_narrative(self, response: AdvisoryForecastResponse) -> RecommendationNarrative:
        if response.stockout_risk == "HIGH":
            summary = "Stockout risk is high and the forecast should be reviewed promptly."
        elif response.stockout_risk == "MEDIUM":
            summary = "Stockout risk is moderate and the forecast should be reviewed for early replenishment planning."
        elif response.stockout_risk == "LOW":
            summary = "Stockout risk is low based on the current advisory forecast."
        else:
            summary = "Stockout risk is unknown because demand or stock evidence is incomplete."

        reasoning = tuple(response.explanation)
        assumptions = (
            "Inventory remains the source of truth.",
            "Forecast output is advisory and requires manager review before operational action.",
        )
        warnings = () if response.evidence_refs else ("Forecast has no evidence references and should be treated with caution.",)
        return RecommendationNarrative(summary=summary, reasoning=reasoning, assumptions=assumptions, warnings=warnings)

    def _build_explanation_lines(
        self,
        response: AdvisoryForecastResponse,
        evidence: EvidenceSummary,
        confidence: ConfidenceBreakdown,
    ) -> list[str]:
        lines = [
            f"Forecast quantity is {response.forecast_quantity:.4f} units over {response.forecast_days} days.",
            f"Stockout risk is {response.stockout_risk}.",
            f"Overall confidence is {confidence.overall:.4f}.",
            f"Evidence references linked: {evidence.evidence_ref_count}.",
        ]
        if response.projected_days_of_cover is None:
            lines.append("Projected days of cover is unavailable because stock or demand evidence is incomplete.")
        else:
            lines.append(f"Projected days of cover is {response.projected_days_of_cover:.4f} days.")
        lines.extend(response.explanation)
        return lines
