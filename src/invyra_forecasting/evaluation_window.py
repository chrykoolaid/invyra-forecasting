from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

from invyra_forecasting.evaluation_linkage import ForecastEvaluationLink
from invyra_forecasting.history import ForecastHistoryRecord


class EvaluationWindowStatus(str, Enum):
    NOT_YET_EVALUABLE = "not_yet_evaluable"
    PARTIALLY_EVALUABLE = "partially_evaluable"
    FULLY_EVALUABLE = "fully_evaluable"
    INSUFFICIENT_ACTUAL_DATA = "insufficient_actual_data"
    EVALUATED = "evaluated"


@dataclass(frozen=True)
class EvaluationWindowAssessment:
    history_id: str
    evaluation_id: str
    forecast_id: str
    forecast_origin_utc: str
    forecast_horizon_end_utc: str
    assessed_at_utc: str
    actual_data_completeness: float
    status: EvaluationWindowStatus
    final_evaluation_eligible: bool
    warnings: tuple[str, ...] = ()
    advisory_only: bool = True
    read_only: bool = True
    inventory_source_of_truth_preserved: bool = True

    def __post_init__(self) -> None:
        if not 0.0 <= self.actual_data_completeness <= 1.0:
            raise ValueError("actual_data_completeness must be between 0.0 and 1.0")
        if not self.advisory_only or not self.read_only:
            raise ValueError("evaluation window assessments must remain advisory-only and read-only")
        if not self.inventory_source_of_truth_preserved:
            raise ValueError("inventory source of truth must be preserved")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["status"] = self.status.value
        payload["warnings"] = list(self.warnings)
        return payload


class EvaluationWindowService:
    """Classifies readiness without creating or modifying evaluations."""

    def assess(
        self,
        history: ForecastHistoryRecord,
        link: ForecastEvaluationLink,
        *,
        assessed_at_utc: str,
        actual_data_completeness: float,
        evaluation_completed: bool = False,
    ) -> EvaluationWindowAssessment:
        self._validate_identity(history, link)
        if not 0.0 <= actual_data_completeness <= 1.0:
            raise ValueError("actual_data_completeness must be between 0.0 and 1.0")

        origin = self._parse_utc(history.created_at_utc, "history.created_at_utc")
        assessed_at = self._parse_utc(assessed_at_utc, "assessed_at_utc")
        horizon_end = origin + timedelta(days=link.forecast_horizon_days)
        warnings: list[str] = []

        if evaluation_completed:
            status = EvaluationWindowStatus.EVALUATED
            eligible = True
        elif assessed_at < origin:
            status = EvaluationWindowStatus.NOT_YET_EVALUABLE
            eligible = False
            warnings.append("assessment precedes the forecast origin")
        elif assessed_at < horizon_end:
            eligible = False
            if actual_data_completeness == 0.0:
                status = EvaluationWindowStatus.NOT_YET_EVALUABLE
                warnings.append("forecast horizon is open and no actual outcome coverage is available")
            else:
                status = EvaluationWindowStatus.PARTIALLY_EVALUABLE
                warnings.append("forecast horizon is open; only partial evaluation is permitted")
        elif actual_data_completeness < 1.0:
            status = EvaluationWindowStatus.INSUFFICIENT_ACTUAL_DATA
            eligible = False
            warnings.append("forecast horizon is complete but actual outcome coverage is incomplete")
        else:
            status = EvaluationWindowStatus.FULLY_EVALUABLE
            eligible = True

        return EvaluationWindowAssessment(
            history_id=history.history_id,
            evaluation_id=link.evaluation_id,
            forecast_id=history.forecast_id,
            forecast_origin_utc=origin.isoformat(),
            forecast_horizon_end_utc=horizon_end.isoformat(),
            assessed_at_utc=assessed_at.isoformat(),
            actual_data_completeness=actual_data_completeness,
            status=status,
            final_evaluation_eligible=eligible,
            warnings=tuple(warnings),
        )

    @staticmethod
    def _validate_identity(history: ForecastHistoryRecord, link: ForecastEvaluationLink) -> None:
        if history.history_id != link.history_id:
            raise ValueError("history and evaluation link history_id must match")
        if history.forecast_id != link.forecast_id:
            raise ValueError("history and evaluation link forecast_id must match")
        if history.version_number != link.history_version_number:
            raise ValueError("history and evaluation link version must match")
        if not history.advisory_only or not history.read_only:
            raise ValueError("history must remain advisory-only and read-only")
        if not link.advisory_only or not link.read_only:
            raise ValueError("evaluation link must remain advisory-only and read-only")
        if not history.inventory_source_of_truth_preserved or not link.inventory_source_of_truth_preserved:
            raise ValueError("inventory source of truth must be preserved")

    @staticmethod
    def _parse_utc(value: str, field_name: str) -> datetime:
        try:
            parsed = datetime.fromisoformat(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{field_name} must be a valid ISO-8601 timestamp") from exc
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError(f"{field_name} must include a UTC offset")
        return parsed.astimezone(timezone.utc)
