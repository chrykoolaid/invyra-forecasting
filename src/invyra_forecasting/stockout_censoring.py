from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Iterable

from invyra_forecasting.actual_outcome import ActualOutcomeEvidence


class StockoutCensoringStatus(str, Enum):
    UNCENSORED = "uncensored"
    PARTIALLY_CENSORED = "partially_stockout_censored"
    FULLY_CENSORED = "fully_stockout_censored"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


@dataclass(frozen=True)
class StockoutCensoringAssessment:
    outcome_evidence_id: str
    forecast_id: str
    item_id: str
    location_id: str
    status: StockoutCensoringStatus
    stockout_coverage: float | None
    stockout_evidence_refs: tuple[str, ...]
    observed_quantity_unchanged: float
    ranking_evidence_eligible: bool
    warnings: tuple[str, ...] = ()
    advisory_only: bool = True
    read_only: bool = True
    inventory_source_of_truth_preserved: bool = True

    def __post_init__(self) -> None:
        if self.stockout_coverage is not None and not 0.0 <= self.stockout_coverage <= 1.0:
            raise ValueError("stockout_coverage must be between 0.0 and 1.0")
        if self.observed_quantity_unchanged < 0:
            raise ValueError("observed_quantity_unchanged must not be negative")
        if not self.advisory_only or not self.read_only:
            raise ValueError("stockout censoring assessments must remain advisory-only and read-only")
        if not self.inventory_source_of_truth_preserved:
            raise ValueError("inventory source of truth must be preserved")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["status"] = self.status.value
        payload["stockout_evidence_refs"] = list(self.stockout_evidence_refs)
        payload["warnings"] = list(self.warnings)
        return payload


class StockoutCensoringService:
    """Classifies explicit stockout evidence without reconstructing demand."""

    def classify(
        self,
        outcome: ActualOutcomeEvidence,
        *,
        stockout_coverage: float | None,
        stockout_evidence_refs: Iterable[str] = (),
    ) -> StockoutCensoringAssessment:
        refs = tuple(stockout_evidence_refs)
        if stockout_coverage is not None and not 0.0 <= stockout_coverage <= 1.0:
            raise ValueError("stockout_coverage must be between 0.0 and 1.0")

        warnings: list[str] = []
        if stockout_coverage is None:
            status = StockoutCensoringStatus.INSUFFICIENT_EVIDENCE
            eligible = False
            warnings.append("stockout coverage was not supplied")
        elif stockout_coverage == 0.0:
            status = StockoutCensoringStatus.UNCENSORED
            eligible = outcome.data_completeness == 1.0
            if outcome.data_completeness < 1.0:
                warnings.append("actual outcome coverage is incomplete")
        else:
            if not refs:
                raise ValueError("stockout evidence references are required when stockout coverage is greater than zero")
            eligible = False
            if stockout_coverage == 1.0:
                status = StockoutCensoringStatus.FULLY_CENSORED
                warnings.append("the measurement window was fully stockout-censored")
            else:
                status = StockoutCensoringStatus.PARTIALLY_CENSORED
                warnings.append("recorded quantity may understate demand because stockout coverage is present")

        return StockoutCensoringAssessment(
            outcome_evidence_id=outcome.outcome_evidence_id,
            forecast_id=outcome.forecast_id,
            item_id=outcome.item_id,
            location_id=outcome.location_id,
            status=status,
            stockout_coverage=stockout_coverage,
            stockout_evidence_refs=refs,
            observed_quantity_unchanged=outcome.observed_quantity,
            ranking_evidence_eligible=eligible,
            warnings=tuple(warnings),
        )
