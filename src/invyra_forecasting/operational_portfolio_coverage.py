from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

from invyra_forecasting.operational_portfolio_breakdown import OperationalForecastPortfolioBreakdown
from invyra_forecasting.operational_portfolio_summary import OperationalForecastPortfolioSummary

OPERATIONAL_PORTFOLIO_COVERAGE_SCHEMA_VERSION = "1.0.0"


class OperationalPortfolioCoverageStatus(str, Enum):
    UNAVAILABLE = "unavailable"
    LIMITED = "limited"
    DEVELOPING = "developing"
    ESTABLISHED = "established"
    COMPLETE = "complete"


@dataclass(frozen=True)
class OperationalPortfolioCoverageAssessment:
    namespace: str
    as_of_utc: str
    status: OperationalPortfolioCoverageStatus
    forecast_record_count: int
    item_count: int
    location_count: int
    item_location_count: int
    evidence_linked_record_count: int
    snapshot_linked_record_count: int
    evidence_coverage_ratio: float | None
    snapshot_coverage_ratio: float | None
    reasons: tuple[str, ...]
    history_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    schema_version: str = OPERATIONAL_PORTFOLIO_COVERAGE_SCHEMA_VERSION
    advisory_only: bool = True
    read_only: bool = True
    inventory_source_of_truth_preserved: bool = True

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["status"] = self.status.value
        payload["reasons"] = list(self.reasons)
        payload["history_refs"] = list(self.history_refs)
        payload["evidence_refs"] = list(self.evidence_refs)
        return payload


class OperationalPortfolioCoveragePolicy:
    """Classifies observed history-linkage coverage without inferring inventory risk."""

    def classify(
        self,
        summary: OperationalForecastPortfolioSummary,
        breakdown: OperationalForecastPortfolioBreakdown,
    ) -> OperationalPortfolioCoverageAssessment:
        _validate_inputs(summary, breakdown)
        total = summary.forecast_record_count
        evidence_ratio = None if total == 0 else summary.evidence_linked_record_count / total
        snapshot_ratio = None if total == 0 else summary.snapshot_linked_record_count / total
        status, reasons = _classify(total, evidence_ratio, snapshot_ratio)

        return OperationalPortfolioCoverageAssessment(
            namespace=summary.namespace,
            as_of_utc=summary.as_of_utc,
            status=status,
            forecast_record_count=total,
            item_count=len(breakdown.items),
            location_count=len(breakdown.locations),
            item_location_count=len(breakdown.item_locations),
            evidence_linked_record_count=summary.evidence_linked_record_count,
            snapshot_linked_record_count=summary.snapshot_linked_record_count,
            evidence_coverage_ratio=evidence_ratio,
            snapshot_coverage_ratio=snapshot_ratio,
            reasons=reasons,
            history_refs=summary.history_refs,
            evidence_refs=summary.evidence_refs,
        )


def _classify(
    total: int,
    evidence_ratio: float | None,
    snapshot_ratio: float | None,
) -> tuple[OperationalPortfolioCoverageStatus, tuple[str, ...]]:
    if total == 0:
        return OperationalPortfolioCoverageStatus.UNAVAILABLE, (
            "No forecast-history records are available for the requested boundary.",
        )
    assert evidence_ratio is not None and snapshot_ratio is not None
    minimum = min(evidence_ratio, snapshot_ratio)
    if minimum < 0.5:
        status = OperationalPortfolioCoverageStatus.LIMITED
    elif minimum < 0.8:
        status = OperationalPortfolioCoverageStatus.DEVELOPING
    elif minimum < 1.0:
        status = OperationalPortfolioCoverageStatus.ESTABLISHED
    else:
        status = OperationalPortfolioCoverageStatus.COMPLETE

    return status, (
        f"Evaluation-evidence linkage covers {evidence_ratio:.1%} of included history records.",
        f"Snapshot linkage covers {snapshot_ratio:.1%} of included history records.",
        "Coverage status describes evidence linkage only and does not classify stock or forecast risk.",
    )


def _validate_inputs(
    summary: OperationalForecastPortfolioSummary,
    breakdown: OperationalForecastPortfolioBreakdown,
) -> None:
    if summary.namespace != breakdown.namespace:
        raise ValueError("coverage inputs must belong to the same tenant namespace")
    if summary.as_of_utc != breakdown.as_of_utc:
        raise ValueError("coverage inputs must use the same as_of_utc boundary")
    if not summary.advisory_only or not breakdown.advisory_only:
        raise ValueError("coverage inputs must remain advisory-only")
    if not summary.read_only or not breakdown.read_only:
        raise ValueError("coverage inputs must remain read-only")
    if not summary.inventory_source_of_truth_preserved or not breakdown.inventory_source_of_truth_preserved:
        raise ValueError("inventory source of truth must be preserved")
    if summary.unique_item_count != len(breakdown.items):
        raise ValueError("item breakdown count must match the operational summary")
    if summary.unique_location_count != len(breakdown.locations):
        raise ValueError("location breakdown count must match the operational summary")
    if summary.unique_item_location_count != len(breakdown.item_locations):
        raise ValueError("item-location breakdown count must match the operational summary")
    breakdown_history_refs = {
        ref for entry in breakdown.item_locations for ref in entry.history_refs
    }
    if set(summary.history_refs) != breakdown_history_refs:
        raise ValueError("breakdown history references must match the operational summary")
