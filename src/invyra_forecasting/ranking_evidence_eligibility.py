from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Iterable

from invyra_forecasting.evaluation_evidence_persistence import (
    EvaluationEvidenceRecord,
    EvaluationEvidenceStage,
)

RANKING_EVIDENCE_POLICY_VERSION = "1.0.0"


class RankingEvidenceExclusionReason(str, Enum):
    NOT_FINAL = "not_final"
    WINDOW_NOT_FINAL_ELIGIBLE = "window_not_final_eligible"
    INCOMPLETE_ACTUAL_DATA = "incomplete_actual_data"
    STOCKOUT_CENSORED = "stockout_censored"
    CENSORING_NOT_RANKING_ELIGIBLE = "censoring_not_ranking_eligible"
    INVALID_MODEL_IDENTITY = "invalid_model_identity"
    INVALID_FORECAST_HORIZON = "invalid_forecast_horizon"
    MISSING_OUTCOME_EVIDENCE = "missing_outcome_evidence"
    IDENTITY_MISMATCH = "identity_mismatch"
    GUARDRAIL_VIOLATION = "guardrail_violation"


@dataclass(frozen=True)
class RankingEvidenceEligibilityDecision:
    record_id: str
    evaluation_id: str
    model_name: str | None
    model_version: str | None
    eligible: bool
    exclusion_reasons: tuple[RankingEvidenceExclusionReason, ...]
    policy_version: str = RANKING_EVIDENCE_POLICY_VERSION
    advisory_only: bool = True
    read_only: bool = True
    inventory_source_of_truth_preserved: bool = True

    def __post_init__(self) -> None:
        if not self.record_id or not self.evaluation_id:
            raise ValueError("record_id and evaluation_id are required")
        if self.eligible and self.exclusion_reasons:
            raise ValueError("eligible evidence cannot contain exclusion reasons")
        if not self.eligible and not self.exclusion_reasons:
            raise ValueError("ineligible evidence must contain at least one exclusion reason")
        if not self.advisory_only or not self.read_only:
            raise ValueError("ranking evidence decisions must remain advisory-only and read-only")
        if not self.inventory_source_of_truth_preserved:
            raise ValueError("inventory source of truth must be preserved")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["exclusion_reasons"] = [reason.value for reason in self.exclusion_reasons]
        return payload


class RankingEvidenceEligibilityPolicy:
    """Certifies evidence for later ranking use without changing any selector."""

    def assess(self, record: EvaluationEvidenceRecord) -> RankingEvidenceEligibilityDecision:
        reasons: list[RankingEvidenceExclusionReason] = []
        linkage = record.linkage
        window = record.window_assessment
        outcome = record.actual_outcome
        censoring = record.censoring_assessment

        if record.stage is not EvaluationEvidenceStage.FINAL:
            reasons.append(RankingEvidenceExclusionReason.NOT_FINAL)
        if window.get("final_evaluation_eligible") is not True:
            reasons.append(RankingEvidenceExclusionReason.WINDOW_NOT_FINAL_ELIGIBLE)
        if outcome.get("data_completeness") != 1.0:
            reasons.append(RankingEvidenceExclusionReason.INCOMPLETE_ACTUAL_DATA)
        if censoring.get("status") != "uncensored":
            reasons.append(RankingEvidenceExclusionReason.STOCKOUT_CENSORED)
        if censoring.get("ranking_evidence_eligible") is not True:
            reasons.append(RankingEvidenceExclusionReason.CENSORING_NOT_RANKING_ELIGIBLE)

        model_name = linkage.get("model_name")
        model_version = linkage.get("model_version")
        if not isinstance(model_name, str) or not model_name.strip() or not isinstance(model_version, str) or not model_version.strip():
            reasons.append(RankingEvidenceExclusionReason.INVALID_MODEL_IDENTITY)

        horizon = linkage.get("forecast_horizon_days")
        if not isinstance(horizon, int) or isinstance(horizon, bool) or horizon < 1:
            reasons.append(RankingEvidenceExclusionReason.INVALID_FORECAST_HORIZON)

        evidence_refs = outcome.get("evidence_refs")
        if not isinstance(evidence_refs, (list, tuple)) or not evidence_refs:
            reasons.append(RankingEvidenceExclusionReason.MISSING_OUTCOME_EVIDENCE)

        if not self._identities_match(record):
            reasons.append(RankingEvidenceExclusionReason.IDENTITY_MISMATCH)
        if not self._guardrails_hold(record):
            reasons.append(RankingEvidenceExclusionReason.GUARDRAIL_VIOLATION)

        unique_reasons = tuple(dict.fromkeys(reasons))
        return RankingEvidenceEligibilityDecision(
            record_id=record.record_id,
            evaluation_id=record.evaluation_id,
            model_name=model_name if isinstance(model_name, str) else None,
            model_version=model_version if isinstance(model_version, str) else None,
            eligible=not unique_reasons,
            exclusion_reasons=unique_reasons,
        )

    def eligible_records(
        self,
        records: Iterable[EvaluationEvidenceRecord],
    ) -> tuple[EvaluationEvidenceRecord, ...]:
        return tuple(record for record in records if self.assess(record).eligible)

    @staticmethod
    def _identities_match(record: EvaluationEvidenceRecord) -> bool:
        linkage = record.linkage
        outcome = record.actual_outcome
        censoring = record.censoring_assessment
        return (
            linkage.get("evaluation_id") == record.evaluation_id
            and linkage.get("history_id") == record.history_id
            and linkage.get("forecast_id") == record.forecast_id
            and outcome.get("forecast_id") == record.forecast_id
            and censoring.get("forecast_id") == record.forecast_id
            and outcome.get("outcome_evidence_id") == record.outcome_evidence_id
            and censoring.get("outcome_evidence_id") == record.outcome_evidence_id
            and outcome.get("item_id") == linkage.get("item_id") == censoring.get("item_id")
            and outcome.get("location_id") == linkage.get("location_id") == censoring.get("location_id")
        )

    @staticmethod
    def _guardrails_hold(record: EvaluationEvidenceRecord) -> bool:
        nested = (
            record.linkage,
            record.window_assessment,
            record.actual_outcome,
            record.censoring_assessment,
        )
        return (
            record.advisory_only
            and record.read_only
            and record.inventory_source_of_truth_preserved
            and all(item.get("advisory_only") is True for item in nested)
            and all(item.get("read_only") is True for item in nested)
            and all(item.get("inventory_source_of_truth_preserved") is True for item in nested)
        )
