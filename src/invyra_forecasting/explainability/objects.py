from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from invyra_forecasting.constants import Environment


class DiagnosticSeverity(StrEnum):
    """Severity levels for explainability diagnostics."""

    INFO = "INFO"
    NOTICE = "NOTICE"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class EvidenceSummary:
    """Enterprise summary of evidence used to explain an advisory forecast."""

    item_id: str
    location_id: str
    environment: Environment
    sales_signal_count: int = 0
    receiving_signal_count: int = 0
    supplier_signal_count: int = 0
    gap_scan_signal_count: int = 0
    shelf_empty_signal_count: int = 0
    markdown_signal_count: int = 0
    transfer_signal_count: int = 0
    wastage_signal_count: int = 0
    adjustment_signal_count: int = 0
    location_stock_signal_count: int = 0
    evidence_ref_count: int = 0
    evidence_refs: tuple[str, ...] = ()
    freshness_notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["environment"] = self.environment.value
        payload["evidence_refs"] = list(self.evidence_refs)
        payload["freshness_notes"] = list(self.freshness_notes)
        return payload


@dataclass(frozen=True)
class ConfidenceBreakdown:
    """Auditable confidence components for a forecast recommendation."""

    overall: float
    signal_quality: float
    evidence_completeness: float
    history_quality: float
    data_freshness: float
    coverage_quality: float
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["notes"] = list(self.notes)
        return payload


@dataclass(frozen=True)
class DiagnosticFinding:
    """Single diagnostic finding raised by explainability analysis."""

    code: str
    severity: DiagnosticSeverity
    message: str
    confidence_impact: float = 0.0
    evidence_refs: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["severity"] = self.severity.value
        payload["evidence_refs"] = list(self.evidence_refs)
        return payload


@dataclass(frozen=True)
class DiagnosticReport:
    """Collection of explainability diagnostics for a forecast."""

    item_id: str
    location_id: str
    environment: Environment
    findings: tuple[DiagnosticFinding, ...] = ()

    @property
    def has_warnings(self) -> bool:
        return any(finding.severity in {DiagnosticSeverity.WARNING, DiagnosticSeverity.CRITICAL} for finding in self.findings)

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "location_id": self.location_id,
            "environment": self.environment.value,
            "has_warnings": self.has_warnings,
            "findings": [finding.to_dict() for finding in self.findings],
        }


@dataclass(frozen=True)
class RecommendationNarrative:
    """Manager-readable recommendation narrative."""

    summary: str
    reasoning: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary,
            "reasoning": list(self.reasoning),
            "assumptions": list(self.assumptions),
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class ForecastExplanation:
    """Enterprise explainability contract for one advisory forecast."""

    item_id: str
    location_id: str
    environment: Environment
    forecast_quantity: float
    forecast_days: int
    stockout_risk: str
    explanation_lines: tuple[str, ...]
    evidence_summary: EvidenceSummary
    confidence_breakdown: ConfidenceBreakdown
    diagnostic_report: DiagnosticReport
    narrative: RecommendationNarrative
    audit_refs: tuple[str, ...] = ()
    advisory_only: bool = True
    inventory_source_of_truth_preserved: bool = True
    created_at_utc: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "location_id": self.location_id,
            "environment": self.environment.value,
            "forecast_quantity": self.forecast_quantity,
            "forecast_days": self.forecast_days,
            "stockout_risk": self.stockout_risk,
            "explanation_lines": list(self.explanation_lines),
            "evidence_summary": self.evidence_summary.to_dict(),
            "confidence_breakdown": self.confidence_breakdown.to_dict(),
            "diagnostic_report": self.diagnostic_report.to_dict(),
            "narrative": self.narrative.to_dict(),
            "audit_refs": list(self.audit_refs),
            "advisory_only": self.advisory_only,
            "inventory_source_of_truth_preserved": self.inventory_source_of_truth_preserved,
            "created_at_utc": self.created_at_utc,
        }
