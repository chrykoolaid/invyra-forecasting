from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

from invyra_forecasting.operational_portfolio_breakdown import OperationalForecastPortfolioBreakdown
from invyra_forecasting.operational_portfolio_coverage import OperationalPortfolioCoverageAssessment

OPERATIONAL_PORTFOLIO_EVIDENCE_SIGNALS_SCHEMA_VERSION = "1.0.0"


class OperationalEvidenceSignalSeverity(str, Enum):
    INFORMATIONAL = "informational"
    WATCH = "watch"


@dataclass(frozen=True)
class OperationalEvidenceSignal:
    code: str
    severity: OperationalEvidenceSignalSeverity
    reason: str
    observed_value: float | int | None
    history_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["severity"] = self.severity.value
        payload["history_refs"] = list(self.history_refs)
        payload["evidence_refs"] = list(self.evidence_refs)
        return payload


@dataclass(frozen=True)
class OperationalPortfolioEvidenceSignalAssessment:
    namespace: str
    as_of_utc: str
    signals: tuple[OperationalEvidenceSignal, ...]
    schema_version: str = OPERATIONAL_PORTFOLIO_EVIDENCE_SIGNALS_SCHEMA_VERSION
    advisory_only: bool = True
    read_only: bool = True
    inventory_source_of_truth_preserved: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "namespace": self.namespace,
            "as_of_utc": self.as_of_utc,
            "signals": [signal.to_dict() for signal in self.signals],
            "schema_version": self.schema_version,
            "advisory_only": self.advisory_only,
            "read_only": self.read_only,
            "inventory_source_of_truth_preserved": self.inventory_source_of_truth_preserved,
        }


class OperationalPortfolioEvidenceSignalPolicy:
    """Reports observed evidence conditions without inferring inventory or forecast risk."""

    def assess(
        self,
        coverage: OperationalPortfolioCoverageAssessment,
        breakdown: OperationalForecastPortfolioBreakdown,
    ) -> OperationalPortfolioEvidenceSignalAssessment:
        _validate_inputs(coverage, breakdown)
        signals: list[OperationalEvidenceSignal] = []

        if coverage.forecast_record_count == 0:
            signals.append(
                OperationalEvidenceSignal(
                    code="no_history",
                    severity=OperationalEvidenceSignalSeverity.INFORMATIONAL,
                    reason="No forecast-history records are available for the requested boundary.",
                    observed_value=0,
                    history_refs=(),
                    evidence_refs=(),
                )
            )
        else:
            _append_linkage_signals(signals, coverage)
            _append_distribution_signals(signals, breakdown)

        return OperationalPortfolioEvidenceSignalAssessment(
            namespace=coverage.namespace,
            as_of_utc=coverage.as_of_utc,
            signals=tuple(signals),
        )


def _append_linkage_signals(
    signals: list[OperationalEvidenceSignal],
    coverage: OperationalPortfolioCoverageAssessment,
) -> None:
    if coverage.evidence_linked_record_count == 0:
        signals.append(
            _signal(
                coverage,
                code="missing_evidence_linkage",
                reason="No included forecast-history records reference evaluation evidence.",
                observed_value=0.0,
            )
        )
    elif coverage.evidence_coverage_ratio is not None and coverage.evidence_coverage_ratio < 1.0:
        signals.append(
            _signal(
                coverage,
                code="incomplete_evidence_linkage",
                reason="Some included forecast-history records do not reference evaluation evidence.",
                observed_value=coverage.evidence_coverage_ratio,
            )
        )

    if coverage.snapshot_linked_record_count == 0:
        signals.append(
            _signal(
                coverage,
                code="missing_snapshot_linkage",
                reason="No included forecast-history records reference a forecast snapshot.",
                observed_value=0.0,
            )
        )
    elif coverage.snapshot_coverage_ratio is not None and coverage.snapshot_coverage_ratio < 1.0:
        signals.append(
            _signal(
                coverage,
                code="incomplete_snapshot_linkage",
                reason="Some included forecast-history records do not reference a forecast snapshot.",
                observed_value=coverage.snapshot_coverage_ratio,
            )
        )


def _append_distribution_signals(
    signals: list[OperationalEvidenceSignal],
    breakdown: OperationalForecastPortfolioBreakdown,
) -> None:
    item_counts = {entry.forecast_record_count for entry in breakdown.items}
    if len(item_counts) > 1:
        signals.append(
            OperationalEvidenceSignal(
                code="uneven_item_history_distribution",
                severity=OperationalEvidenceSignalSeverity.INFORMATIONAL,
                reason="Included forecast-history record counts differ across items.",
                observed_value=len(item_counts),
                history_refs=_history_refs(breakdown.items),
                evidence_refs=_evidence_refs(breakdown.items),
            )
        )

    location_counts = {entry.forecast_record_count for entry in breakdown.locations}
    if len(location_counts) > 1:
        signals.append(
            OperationalEvidenceSignal(
                code="uneven_location_history_distribution",
                severity=OperationalEvidenceSignalSeverity.INFORMATIONAL,
                reason="Included forecast-history record counts differ across locations.",
                observed_value=len(location_counts),
                history_refs=_history_refs(breakdown.locations),
                evidence_refs=_evidence_refs(breakdown.locations),
            )
        )


def _signal(
    coverage: OperationalPortfolioCoverageAssessment,
    *,
    code: str,
    reason: str,
    observed_value: float,
) -> OperationalEvidenceSignal:
    return OperationalEvidenceSignal(
        code=code,
        severity=OperationalEvidenceSignalSeverity.WATCH,
        reason=reason,
        observed_value=observed_value,
        history_refs=coverage.history_refs,
        evidence_refs=coverage.evidence_refs,
    )


def _history_refs(entries) -> tuple[str, ...]:
    return tuple(sorted({ref for entry in entries for ref in entry.history_refs}))


def _evidence_refs(entries) -> tuple[str, ...]:
    return tuple(sorted({ref for entry in entries for ref in entry.evidence_refs}))


def _validate_inputs(
    coverage: OperationalPortfolioCoverageAssessment,
    breakdown: OperationalForecastPortfolioBreakdown,
) -> None:
    if coverage.namespace != breakdown.namespace:
        raise ValueError("evidence signal inputs must belong to the same tenant namespace")
    if coverage.as_of_utc != breakdown.as_of_utc:
        raise ValueError("evidence signal inputs must use the same as_of_utc boundary")
    if not coverage.advisory_only or not breakdown.advisory_only:
        raise ValueError("evidence signal inputs must remain advisory-only")
    if not coverage.read_only or not breakdown.read_only:
        raise ValueError("evidence signal inputs must remain read-only")
    if not coverage.inventory_source_of_truth_preserved or not breakdown.inventory_source_of_truth_preserved:
        raise ValueError("inventory source of truth must be preserved")
    breakdown_refs = {ref for entry in breakdown.item_locations for ref in entry.history_refs}
    if set(coverage.history_refs) != breakdown_refs:
        raise ValueError("breakdown history references must match the coverage assessment")
