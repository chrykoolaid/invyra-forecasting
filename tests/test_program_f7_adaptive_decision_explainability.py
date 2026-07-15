from dataclasses import FrozenInstanceError

import pytest

from invyra_forecasting.adaptive_decision_explainability import (
    AdaptiveDecisionExplainabilityService,
)
from invyra_forecasting.adaptive_selection_inputs import (
    AdaptiveSelectionCandidateInput,
    AdaptiveSelectionContext,
    AdaptiveSelectionInputPackage,
)
from invyra_forecasting.models.performance_selection import (
    AdaptiveRankingConfiguration,
    ModelPerformanceScore,
    ModelSelectionAuditRecord,
    ModelSelectionContext,
)


def _candidate(registry_id: str, model_name: str, score_ref: str):
    return AdaptiveSelectionCandidateInput(
        registry_id=registry_id,
        model_name=model_name,
        model_version="1.0",
        lifecycle_status="active",
        forecast_horizon_days=7,
        horizon_supported=True,
        demand_profile="seasonal",
        demand_profile_supported=True,
        eligible_evaluation_count=40,
        confidence_status="trusted",
        mae=2.0,
        rmse=2.5,
        mape=0.2,
        bias=0.01,
        average_accuracy_score=0.9,
        average_calibration_gap=0.03,
        qualification_reasons=("30 to 99 certified evaluations",),
        evidence_refs=(score_ref,),
    )


def _package():
    return AdaptiveSelectionInputPackage(
        context=AdaptiveSelectionContext(
            forecast_horizon_days=7,
            demand_profile="seasonal",
            item_id="item-1",
            location_id="loc-1",
        ),
        candidates=(
            _candidate("reg-a", "seasonal-naive", "evaluation-a"),
            _candidate("reg-b", "moving-average", "evaluation-b"),
        ),
    )


def _audit():
    return ModelSelectionAuditRecord(
        selected_model_id="model-a",
        candidate_scores=(
            ModelPerformanceScore(
                model_id="model-a",
                score=0.91,
                components={"accuracy": 0.95, "context_fit": 0.9},
                rationale=("highest governed adaptive score",),
                warnings=(),
            ),
            ModelPerformanceScore(
                model_id="model-b",
                score=0.84,
                components={"accuracy": 0.86, "context_fit": 0.82},
                rationale=("considered as an eligible alternative",),
                warnings=("lower context fit",),
            ),
        ),
        context=ModelSelectionContext(
            forecast_type="demand",
            forecast_days=7,
            item_id="item-1",
            location_id="loc-1",
            demand_pattern="seasonal",
        ),
        ranking_configuration=AdaptiveRankingConfiguration(version="7A.1"),
        created_at="2026-07-16T00:00:00+00:00",
    )


def test_explains_selected_model_alternatives_and_evidence() -> None:
    explanation = AdaptiveDecisionExplainabilityService().explain(
        audit_record=_audit(),
        input_package=_package(),
        model_id_by_registry_id={"reg-a": "model-a", "reg-b": "model-b"},
    )

    assert explanation.selected_model_id == "model-a"
    assert explanation.selected_model_name == "seasonal-naive"
    assert explanation.alternatives_considered == ("model-b",)
    assert explanation.ranking_configuration_version == "7A.1"
    selected = next(item for item in explanation.candidates if item.selected)
    assert selected.confidence_status == "trusted"
    assert selected.evidence_refs == ("evaluation-a",)
    assert selected.score_components["accuracy"] == 0.95


def test_preserves_existing_scores_and_rationale_without_rescoring() -> None:
    audit = _audit()
    explanation = AdaptiveDecisionExplainabilityService().explain(
        audit_record=audit,
        input_package=_package(),
        model_id_by_registry_id={"reg-a": "model-a", "reg-b": "model-b"},
    )

    assert [item.score for item in explanation.candidates] == [0.91, 0.84]
    assert explanation.candidates[0].rationale == audit.candidate_scores[0].rationale
    service = AdaptiveDecisionExplainabilityService()
    assert not hasattr(service, "score_model")
    assert not hasattr(service, "rank_models")
    assert not hasattr(service, "select")


def test_rejects_candidate_or_horizon_mismatch() -> None:
    with pytest.raises(ValueError, match="exactly match"):
        AdaptiveDecisionExplainabilityService().explain(
            audit_record=_audit(),
            input_package=_package(),
            model_id_by_registry_id={"reg-a": "model-a", "reg-b": "wrong-model"},
        )

    audit = ModelSelectionAuditRecord(
        selected_model_id="model-a",
        candidate_scores=_audit().candidate_scores,
        context=ModelSelectionContext(forecast_type="demand", forecast_days=14),
    )
    with pytest.raises(ValueError, match="horizons must match"):
        AdaptiveDecisionExplainabilityService().explain(
            audit_record=audit,
            input_package=_package(),
            model_id_by_registry_id={"reg-a": "model-a", "reg-b": "model-b"},
        )


def test_explanation_is_immutable_serializable_and_guarded() -> None:
    explanation = AdaptiveDecisionExplainabilityService().explain(
        audit_record=_audit(),
        input_package=_package(),
        model_id_by_registry_id={"reg-a": "model-a", "reg-b": "model-b"},
    )

    with pytest.raises(FrozenInstanceError):
        explanation.selected_model_id = "model-b"
    payload = explanation.to_dict()
    assert payload["advisory_only"] is True
    assert payload["read_only"] is True
    assert payload["inventory_source_of_truth_preserved"] is True
    assert payload["candidates"][1]["warnings"] == ["lower context fit"]
