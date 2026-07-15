from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Iterable

from invyra_forecasting.evaluation_linkage import ForecastEvaluationLink
from invyra_forecasting.evaluation_window import EvaluationWindowAssessment


@dataclass(frozen=True)
class ActualOutcomeEvidence:
    """Normalized, read-only actual-outcome evidence for forecast evaluation."""

    outcome_evidence_id: str
    forecast_id: str
    item_id: str
    location_id: str
    window_start_utc: str
    window_end_utc: str
    observed_quantity: float
    outcome_source: str
    evidence_refs: tuple[str, ...]
    data_completeness: float
    notes: tuple[str, ...] = ()
    advisory_only: bool = True
    read_only: bool = True
    inventory_source_of_truth_preserved: bool = True

    def __post_init__(self) -> None:
        required = {
            "outcome_evidence_id": self.outcome_evidence_id,
            "forecast_id": self.forecast_id,
            "item_id": self.item_id,
            "location_id": self.location_id,
            "outcome_source": self.outcome_source,
        }
        for field_name, value in required.items():
            if not value:
                raise ValueError(f"{field_name} is required")
        if self.observed_quantity < 0:
            raise ValueError("observed_quantity must not be negative")
        if not 0.0 <= self.data_completeness <= 1.0:
            raise ValueError("data_completeness must be between 0.0 and 1.0")
        if not self.evidence_refs:
            raise ValueError("at least one evidence reference is required")
        start = _parse_utc(self.window_start_utc, "window_start_utc")
        end = _parse_utc(self.window_end_utc, "window_end_utc")
        if end <= start:
            raise ValueError("window_end_utc must be after window_start_utc")
        if not self.advisory_only or not self.read_only:
            raise ValueError("actual outcome evidence must remain advisory-only and read-only")
        if not self.inventory_source_of_truth_preserved:
            raise ValueError("inventory source of truth must be preserved")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["evidence_refs"] = list(self.evidence_refs)
        payload["notes"] = list(self.notes)
        return payload


class ActualOutcomeEvidenceService:
    """Builds normalized evidence without ingesting or mutating operational data."""

    def normalize(
        self,
        link: ForecastEvaluationLink,
        assessment: EvaluationWindowAssessment,
        *,
        outcome_evidence_id: str,
        window_start_utc: str,
        window_end_utc: str,
        observed_quantity: float,
        outcome_source: str,
        evidence_refs: Iterable[str],
        data_completeness: float,
        notes: Iterable[str] = (),
    ) -> ActualOutcomeEvidence:
        self._validate_identity(link, assessment)
        if data_completeness != assessment.actual_data_completeness:
            raise ValueError("outcome evidence completeness must match the evaluation window assessment")
        return ActualOutcomeEvidence(
            outcome_evidence_id=outcome_evidence_id,
            forecast_id=link.forecast_id,
            item_id=link.item_id,
            location_id=link.location_id,
            window_start_utc=_parse_utc(window_start_utc, "window_start_utc").isoformat(),
            window_end_utc=_parse_utc(window_end_utc, "window_end_utc").isoformat(),
            observed_quantity=observed_quantity,
            outcome_source=outcome_source,
            evidence_refs=tuple(evidence_refs),
            data_completeness=data_completeness,
            notes=tuple(notes),
        )

    @staticmethod
    def _validate_identity(
        link: ForecastEvaluationLink,
        assessment: EvaluationWindowAssessment,
    ) -> None:
        if link.history_id != assessment.history_id:
            raise ValueError("evaluation link and assessment history_id must match")
        if link.evaluation_id != assessment.evaluation_id:
            raise ValueError("evaluation link and assessment evaluation_id must match")
        if link.forecast_id != assessment.forecast_id:
            raise ValueError("evaluation link and assessment forecast_id must match")
        if not link.advisory_only or not assessment.advisory_only:
            raise ValueError("linked evidence must remain advisory-only")
        if not link.read_only or not assessment.read_only:
            raise ValueError("linked evidence must remain read-only")
        if (
            not link.inventory_source_of_truth_preserved
            or not assessment.inventory_source_of_truth_preserved
        ):
            raise ValueError("inventory source of truth must be preserved")


def _parse_utc(value: str, field_name: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a valid ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field_name} must include a UTC offset")
    return parsed.astimezone(timezone.utc)
