from __future__ import annotations

from dataclasses import replace

from invyra_forecasting.evaluation_evidence_persistence import (
    EvaluationEvidenceRecord,
    EvaluationEvidenceStage,
)
from invyra_forecasting.ranking_evidence_eligibility import (
    RANKING_EVIDENCE_POLICY_VERSION,
    RankingEvidenceEligibilityPolicy,
    RankingEvidenceExclusionReason,
)


def _record(**overrides) -> EvaluationEvidenceRecord:
    values = {
        "record_id": "record-e7",
        "evaluation_id": "evaluation-e7",
        "history_id": "history-e7",
        "forecast_id": "forecast-e7",
        "outcome_evidence_id": "outcome-e7",
        "stage": EvaluationEvidenceStage.FINAL,
        "linkage": {
            "evaluation_id": "evaluation-e7",
            "history_id": "history-e7",
            "forecast_id": "forecast-e7",
            "item_id": "item-e7",
            "location_id": "location-e7",
            "model_name": "seasonal-naive",
            "model_version": "1.0",
            "forecast_horizon_days": 7,
            "advisory_only": True,
            "read_only": True,
            "inventory_source_of_truth_preserved": True,
        },
        "window_assessment": {
            "final_evaluation_eligible": True,
            "advisory_only": True,
            "read_only": True,
            "inventory_source_of_truth_preserved": True,
        },
        "actual_outcome": {
            "outcome_evidence_id": "outcome-e7",
            "forecast_id": "forecast-e7",
            "item_id": "item-e7",
            "location_id": "location-e7",
            "data_completeness": 1.0,
            "evidence_refs": ["ledger-e7"],
            "advisory_only": True,
            "read_only": True,
            "inventory_source_of_truth_preserved": True,
        },
        "censoring_assessment": {
            "outcome_evidence_id": "outcome-e7",
            "forecast_id": "forecast-e7",
            "item_id": "item-e7",
            "location_id": "location-e7",
            "status": "uncensored",
            "ranking_evidence_eligible": True,
            "advisory_only": True,
            "read_only": True,
            "inventory_source_of_truth_preserved": True,
        },
        "namespace": "default",
    }
    values.update(overrides)
    return EvaluationEvidenceRecord(**values)


def test_complete_final_uncensored_evidence_is_eligible() -> None:
    decision = RankingEvidenceEligibilityPolicy().assess(_record())

    assert decision.eligible is True
    assert decision.exclusion_reasons == ()
    assert decision.policy_version == RANKING_EVIDENCE_POLICY_VERSION
    assert decision.model_name == "seasonal-naive"
    assert decision.model_version == "1.0"


def test_partial_evidence_is_excluded_without_changing_record() -> None:
    record = replace(_record(), stage=EvaluationEvidenceStage.PARTIAL)

    decision = RankingEvidenceEligibilityPolicy().assess(record)

    assert decision.eligible is False
    assert decision.exclusion_reasons == (RankingEvidenceExclusionReason.NOT_FINAL,)
    assert record.stage is EvaluationEvidenceStage.PARTIAL


def test_incomplete_or_censored_evidence_returns_explicit_reasons() -> None:
    outcome = {**_record().actual_outcome, "data_completeness": 0.8}
    censoring = {
        **_record().censoring_assessment,
        "status": "partially_stockout_censored",
        "ranking_evidence_eligible": False,
    }

    decision = RankingEvidenceEligibilityPolicy().assess(
        replace(_record(), actual_outcome=outcome, censoring_assessment=censoring)
    )

    assert decision.eligible is False
    assert decision.exclusion_reasons == (
        RankingEvidenceExclusionReason.INCOMPLETE_ACTUAL_DATA,
        RankingEvidenceExclusionReason.STOCKOUT_CENSORED,
        RankingEvidenceExclusionReason.CENSORING_NOT_RANKING_ELIGIBLE,
    )


def test_invalid_identity_horizon_and_evidence_are_excluded() -> None:
    linkage = {
        **_record().linkage,
        "model_name": "",
        "forecast_horizon_days": 0,
    }
    outcome = {
        **_record().actual_outcome,
        "forecast_id": "other-forecast",
        "evidence_refs": [],
    }

    decision = RankingEvidenceEligibilityPolicy().assess(
        replace(_record(), linkage=linkage, actual_outcome=outcome)
    )

    assert decision.eligible is False
    assert RankingEvidenceExclusionReason.INVALID_MODEL_IDENTITY in decision.exclusion_reasons
    assert RankingEvidenceExclusionReason.INVALID_FORECAST_HORIZON in decision.exclusion_reasons
    assert RankingEvidenceExclusionReason.MISSING_OUTCOME_EVIDENCE in decision.exclusion_reasons
    assert RankingEvidenceExclusionReason.IDENTITY_MISMATCH in decision.exclusion_reasons


def test_guardrail_violation_is_excluded() -> None:
    outcome = {**_record().actual_outcome, "read_only": False}

    decision = RankingEvidenceEligibilityPolicy().assess(
        replace(_record(), actual_outcome=outcome)
    )

    assert decision.eligible is False
    assert decision.exclusion_reasons == (
        RankingEvidenceExclusionReason.GUARDRAIL_VIOLATION,
    )


def test_eligible_records_filters_without_ranking_or_scoring() -> None:
    eligible = _record(record_id="eligible")
    partial = replace(_record(record_id="partial"), stage=EvaluationEvidenceStage.PARTIAL)

    selected = RankingEvidenceEligibilityPolicy().eligible_records((partial, eligible))

    assert selected == (eligible,)
    payload = RankingEvidenceEligibilityPolicy().assess(eligible).to_dict()
    assert "score" not in payload
    assert "rank" not in payload
    assert payload["advisory_only"] is True
    assert payload["read_only"] is True
    assert payload["inventory_source_of_truth_preserved"] is True
