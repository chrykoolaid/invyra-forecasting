from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from invyra_forecasting.enterprise_forecast_health import EnterpriseForecastHealth
from invyra_forecasting.enterprise_intelligence_summary import EnterpriseForecastIntelligenceSummary
from invyra_forecasting.enterprise_portfolio_comparison import EnterprisePortfolioComparison
from invyra_forecasting.enterprise_portfolio_risk import EnterprisePortfolioRiskAssessment

EXECUTIVE_INTELLIGENCE_BRIEF_SCHEMA_VERSION = "1.0.0"


@dataclass(frozen=True)
class ExecutiveIntelligenceBrief:
    namespace: str
    as_of_utc: str
    summary: EnterpriseForecastIntelligenceSummary
    health: EnterpriseForecastHealth
    risks: EnterprisePortfolioRiskAssessment
    comparison: EnterprisePortfolioComparison | None
    brief_reasons: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    schema_version: str = EXECUTIVE_INTELLIGENCE_BRIEF_SCHEMA_VERSION
    advisory_only: bool = True
    read_only: bool = True
    inventory_source_of_truth_preserved: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "namespace": self.namespace,
            "as_of_utc": self.as_of_utc,
            "summary": self.summary.to_dict(),
            "health": self.health.to_dict(),
            "risks": self.risks.to_dict(),
            "comparison": None if self.comparison is None else self.comparison.to_dict(),
            "brief_reasons": list(self.brief_reasons),
            "evidence_refs": list(self.evidence_refs),
            "schema_version": self.schema_version,
            "advisory_only": self.advisory_only,
            "read_only": self.read_only,
            "inventory_source_of_truth_preserved": self.inventory_source_of_truth_preserved,
        }


class ExecutiveIntelligenceBriefService:
    """Composes certified intelligence views without creating new analytics or actions."""

    def compose(
        self,
        summary: EnterpriseForecastIntelligenceSummary,
        health: EnterpriseForecastHealth,
        risks: EnterprisePortfolioRiskAssessment,
        comparison: EnterprisePortfolioComparison | None = None,
    ) -> ExecutiveIntelligenceBrief:
        items = (summary, health, risks) + (() if comparison is None else (comparison,))
        namespaces = {item.namespace for item in items}
        if len(namespaces) != 1:
            raise ValueError("executive brief inputs require matching tenant namespaces")
        if health.as_of_utc != summary.as_of_utc or risks.as_of_utc != summary.as_of_utc:
            raise ValueError("executive brief current-state timestamps must match")
        if comparison is not None and comparison.current_as_of_utc != summary.as_of_utc:
            raise ValueError("comparison current timestamp must match the brief timestamp")
        if any(not item.advisory_only or not item.read_only for item in items):
            raise ValueError("executive brief inputs must remain advisory-only and read-only")
        if any(not item.inventory_source_of_truth_preserved for item in items):
            raise ValueError("inventory source of truth must be preserved")

        refs = set(health.evidence_refs)
        for signal in risks.signals:
            refs.update(signal.evidence_refs)
        if comparison is not None:
            refs.update(comparison.evidence_refs)
        return ExecutiveIntelligenceBrief(
            namespace=summary.namespace,
            as_of_utc=summary.as_of_utc,
            summary=summary,
            health=health,
            risks=risks,
            comparison=comparison,
            brief_reasons=(
                "brief composes existing certified intelligence without recalculating source metrics",
                "brief contains observations only and does not recommend or execute actions",
            ),
            evidence_refs=tuple(sorted(refs)),
        )
