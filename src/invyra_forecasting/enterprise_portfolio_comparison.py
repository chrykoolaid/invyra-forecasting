from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from invyra_forecasting.enterprise_intelligence_summary import EnterpriseForecastIntelligenceSummary

ENTERPRISE_PORTFOLIO_COMPARISON_SCHEMA_VERSION = "1.0.0"


@dataclass(frozen=True)
class EnterprisePortfolioComparison:
    namespace: str
    baseline_as_of_utc: str
    current_as_of_utc: str
    model_version_count_delta: int
    evaluated_model_version_count_delta: int
    eligible_evaluation_count_delta: int
    accuracy_delta: float | None
    calibration_gap_delta: float | None
    comparison_reasons: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    schema_version: str = ENTERPRISE_PORTFOLIO_COMPARISON_SCHEMA_VERSION
    advisory_only: bool = True
    read_only: bool = True
    inventory_source_of_truth_preserved: bool = True

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["comparison_reasons"] = list(self.comparison_reasons)
        payload["evidence_refs"] = list(self.evidence_refs)
        return payload


class EnterprisePortfolioComparisonService:
    """Computes signed portfolio deltas without declaring winners or recommending action."""

    def compare(
        self,
        baseline: EnterpriseForecastIntelligenceSummary,
        current: EnterpriseForecastIntelligenceSummary,
    ) -> EnterprisePortfolioComparison:
        if baseline.namespace != current.namespace:
            raise ValueError("portfolio comparisons require matching tenant namespaces")
        if _parse_timestamp(current.as_of_utc) < _parse_timestamp(baseline.as_of_utc):
            raise ValueError("current_as_of_utc must not precede baseline_as_of_utc")
        guarded = (baseline, current)
        if any(not item.advisory_only or not item.read_only for item in guarded):
            raise ValueError("portfolio comparisons require advisory-only read-only summaries")
        if any(not item.inventory_source_of_truth_preserved for item in guarded):
            raise ValueError("inventory source of truth must be preserved")

        reasons = (
            "signed deltas describe current values minus baseline values",
            "positive or negative deltas do not declare a preferred portfolio state",
        )
        refs = tuple(sorted({ref for summary in guarded for model in summary.models for ref in model.evidence_refs}))
        return EnterprisePortfolioComparison(
            namespace=current.namespace,
            baseline_as_of_utc=baseline.as_of_utc,
            current_as_of_utc=current.as_of_utc,
            model_version_count_delta=current.model_version_count - baseline.model_version_count,
            evaluated_model_version_count_delta=current.evaluated_model_version_count - baseline.evaluated_model_version_count,
            eligible_evaluation_count_delta=current.total_eligible_evaluation_count - baseline.total_eligible_evaluation_count,
            accuracy_delta=_optional_delta(baseline.weighted_average_accuracy_score, current.weighted_average_accuracy_score),
            calibration_gap_delta=_optional_delta(baseline.weighted_average_calibration_gap, current.weighted_average_calibration_gap),
            comparison_reasons=reasons,
            evidence_refs=refs,
        )


def _optional_delta(baseline: float | None, current: float | None) -> float | None:
    if baseline is None or current is None:
        return None
    return round(current - baseline, 4)


def _parse_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("comparison timestamps must be valid ISO-8601 timestamps") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("comparison timestamps must include a UTC offset")
    return parsed
