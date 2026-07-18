from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from invyra_forecasting.enterprise_forecast_health import EnterpriseForecastHealth
from invyra_forecasting.enterprise_intelligence_summary import EnterpriseForecastIntelligenceSummary
from invyra_forecasting.enterprise_portfolio_risk import EnterprisePortfolioRiskAssessment
from invyra_forecasting.operational_portfolio_coverage import OperationalPortfolioCoverageAssessment
from invyra_forecasting.operational_portfolio_evidence_signals import (
    OperationalPortfolioEvidenceSignalAssessment,
)
from invyra_forecasting.operational_portfolio_summary import OperationalForecastPortfolioSummary

DECISION_CONTEXT_SCHEMA_VERSION = "1.0.0"


@dataclass(frozen=True)
class DecisionContext:
    namespace: str
    as_of_utc: str
    enterprise_summary: EnterpriseForecastIntelligenceSummary
    enterprise_health: EnterpriseForecastHealth
    enterprise_risks: EnterprisePortfolioRiskAssessment
    operational_summary: OperationalForecastPortfolioSummary
    operational_coverage: OperationalPortfolioCoverageAssessment
    operational_evidence_signals: OperationalPortfolioEvidenceSignalAssessment
    evidence_refs: tuple[str, ...]
    history_refs: tuple[str, ...]
    schema_version: str = DECISION_CONTEXT_SCHEMA_VERSION
    advisory_only: bool = True
    read_only: bool = True
    inventory_source_of_truth_preserved: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "namespace": self.namespace,
            "as_of_utc": self.as_of_utc,
            "enterprise_summary": self.enterprise_summary.to_dict(),
            "enterprise_health": self.enterprise_health.to_dict(),
            "enterprise_risks": self.enterprise_risks.to_dict(),
            "operational_summary": self.operational_summary.to_dict(),
            "operational_coverage": self.operational_coverage.to_dict(),
            "operational_evidence_signals": self.operational_evidence_signals.to_dict(),
            "evidence_refs": list(self.evidence_refs),
            "history_refs": list(self.history_refs),
            "schema_version": self.schema_version,
            "advisory_only": self.advisory_only,
            "read_only": self.read_only,
            "inventory_source_of_truth_preserved": self.inventory_source_of_truth_preserved,
        }


class DecisionContextService:
    """Composes certified intelligence without scoring, ranking, or recommending action."""

    def compose(
        self,
        enterprise_summary: EnterpriseForecastIntelligenceSummary,
        enterprise_health: EnterpriseForecastHealth,
        enterprise_risks: EnterprisePortfolioRiskAssessment,
        operational_summary: OperationalForecastPortfolioSummary,
        operational_coverage: OperationalPortfolioCoverageAssessment,
        operational_evidence_signals: OperationalPortfolioEvidenceSignalAssessment,
    ) -> DecisionContext:
        inputs = (
            enterprise_summary,
            enterprise_health,
            enterprise_risks,
            operational_summary,
            operational_coverage,
            operational_evidence_signals,
        )
        _validate_inputs(inputs)
        namespace = enterprise_summary.namespace
        as_of_utc = enterprise_summary.as_of_utc

        evidence_refs = set(enterprise_health.evidence_refs)
        for signal in enterprise_risks.signals:
            evidence_refs.update(signal.evidence_refs)
        evidence_refs.update(operational_summary.evidence_refs)
        evidence_refs.update(operational_coverage.evidence_refs)
        for signal in operational_evidence_signals.signals:
            evidence_refs.update(signal.evidence_refs)

        history_refs = set(operational_summary.history_refs)
        history_refs.update(operational_coverage.history_refs)
        for signal in operational_evidence_signals.signals:
            history_refs.update(signal.history_refs)

        return DecisionContext(
            namespace=namespace,
            as_of_utc=as_of_utc,
            enterprise_summary=enterprise_summary,
            enterprise_health=enterprise_health,
            enterprise_risks=enterprise_risks,
            operational_summary=operational_summary,
            operational_coverage=operational_coverage,
            operational_evidence_signals=operational_evidence_signals,
            evidence_refs=tuple(sorted(evidence_refs)),
            history_refs=tuple(sorted(history_refs)),
        )


def _validate_inputs(inputs: tuple[Any, ...]) -> None:
    namespaces = {item.namespace for item in inputs}
    if len(namespaces) != 1:
        raise ValueError("decision context inputs must belong to the same tenant namespace")
    timestamps = {item.as_of_utc for item in inputs}
    if len(timestamps) != 1:
        raise ValueError("decision context inputs must use the same as_of_utc boundary")
    if any(not item.advisory_only or not item.read_only for item in inputs):
        raise ValueError("decision context inputs must remain advisory-only and read-only")
    if any(not item.inventory_source_of_truth_preserved for item in inputs):
        raise ValueError("inventory source of truth must be preserved")
