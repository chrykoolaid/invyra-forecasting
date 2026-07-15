from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

from invyra_forecasting.adaptive_selection_inputs import AdaptiveSelectionInputPackage
from invyra_forecasting.models.performance_selection import ModelSelectionAuditRecord

ADAPTIVE_DECISION_EXPLAINABILITY_SCHEMA_VERSION = "1.0.0"


@dataclass(frozen=True)
class AdaptiveCandidateExplanation:
    model_id: str
    registry_id: str
    model_name: str
    model_version: str
    selected: bool
    score: float
    score_components: Mapping[str, float]
    lifecycle_status: str
    confidence_status: str
    eligible_evaluation_count: int
    horizon_supported: bool
    demand_profile_supported: bool | None
    rationale: tuple[str, ...]
    warnings: tuple[str, ...]
    qualification_reasons: tuple[str, ...]
    evidence_refs: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["score_components"] = dict(self.score_components)
        for field_name in (
            "rationale",
            "warnings",
            "qualification_reasons",
            "evidence_refs",
        ):
            payload[field_name] = list(getattr(self, field_name))
        return payload


@dataclass(frozen=True)
class AdaptiveDecisionExplanation:
    selected_model_id: str
    selected_registry_id: str
    selected_model_name: str
    selected_model_version: str
    selection_summary: tuple[str, ...]
    alternatives_considered: tuple[str, ...]
    candidates: tuple[AdaptiveCandidateExplanation, ...]
    ranking_configuration_version: str
    created_at: str
    schema_version: str = ADAPTIVE_DECISION_EXPLAINABILITY_SCHEMA_VERSION
    advisory_only: bool = True
    read_only: bool = True
    inventory_source_of_truth_preserved: bool = True

    def __post_init__(self) -> None:
        if not self.selected_model_id or not self.selected_registry_id:
            raise ValueError("selected model identity is required")
        if not self.selection_summary:
            raise ValueError("selection_summary is required")
        if not self.candidates:
            raise ValueError("at least one candidate explanation is required")
        if sum(candidate.selected for candidate in self.candidates) != 1:
            raise ValueError("exactly one candidate must be selected")
        if self.schema_version != ADAPTIVE_DECISION_EXPLAINABILITY_SCHEMA_VERSION:
            raise ValueError("unsupported adaptive decision explainability schema version")
        if not self.advisory_only or not self.read_only:
            raise ValueError("adaptive decision explanations must remain advisory-only and read-only")
        if not self.inventory_source_of_truth_preserved:
            raise ValueError("inventory source of truth must be preserved")

    def to_dict(self) -> dict[str, Any]:
        return {
            "selected_model_id": self.selected_model_id,
            "selected_registry_id": self.selected_registry_id,
            "selected_model_name": self.selected_model_name,
            "selected_model_version": self.selected_model_version,
            "selection_summary": list(self.selection_summary),
            "alternatives_considered": list(self.alternatives_considered),
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "ranking_configuration_version": self.ranking_configuration_version,
            "created_at": self.created_at,
            "schema_version": self.schema_version,
            "advisory_only": self.advisory_only,
            "read_only": self.read_only,
            "inventory_source_of_truth_preserved": self.inventory_source_of_truth_preserved,
        }


class AdaptiveDecisionExplainabilityService:
    """Explains an existing adaptive decision without rescoring or reselection."""

    def explain(
        self,
        *,
        audit_record: ModelSelectionAuditRecord,
        input_package: AdaptiveSelectionInputPackage,
        model_id_by_registry_id: Mapping[str, str],
    ) -> AdaptiveDecisionExplanation:
        if not audit_record.candidate_scores:
            raise ValueError("audit record must contain candidate scores")
        if audit_record.context.forecast_days != input_package.context.forecast_horizon_days:
            raise ValueError("audit and governed input horizons must match")

        candidates_by_model_id = {}
        for candidate in input_package.candidates:
            model_id = model_id_by_registry_id.get(candidate.registry_id)
            if not model_id:
                raise ValueError(f"missing model ID mapping for registry entry: {candidate.registry_id}")
            if model_id in candidates_by_model_id:
                raise ValueError("model ID mappings must be unique")
            candidates_by_model_id[model_id] = candidate

        scored_ids = {score.model_id for score in audit_record.candidate_scores}
        if scored_ids != set(candidates_by_model_id):
            raise ValueError("audit candidates must exactly match the governed input package")
        if audit_record.selected_model_id not in scored_ids:
            raise ValueError("selected model must be present in the candidate scores")

        explanations: list[AdaptiveCandidateExplanation] = []
        selected_input = None
        for score in audit_record.candidate_scores:
            candidate = candidates_by_model_id[score.model_id]
            selected = score.model_id == audit_record.selected_model_id
            if selected:
                selected_input = candidate
            explanations.append(
                AdaptiveCandidateExplanation(
                    model_id=score.model_id,
                    registry_id=candidate.registry_id,
                    model_name=candidate.model_name,
                    model_version=candidate.model_version,
                    selected=selected,
                    score=score.score,
                    score_components=dict(score.components),
                    lifecycle_status=candidate.lifecycle_status,
                    confidence_status=candidate.confidence_status,
                    eligible_evaluation_count=candidate.eligible_evaluation_count,
                    horizon_supported=candidate.horizon_supported,
                    demand_profile_supported=candidate.demand_profile_supported,
                    rationale=score.rationale,
                    warnings=score.warnings,
                    qualification_reasons=candidate.qualification_reasons,
                    evidence_refs=candidate.evidence_refs,
                )
            )

        assert selected_input is not None
        selected_score = next(
            score for score in audit_record.candidate_scores
            if score.model_id == audit_record.selected_model_id
        )
        ordered_alternatives = tuple(
            score.model_id
            for score in audit_record.candidate_scores
            if score.model_id != audit_record.selected_model_id
        )
        summary = (
            f"Selected {selected_input.model_name} {selected_input.model_version} with advisory score {selected_score.score:.6f}.",
            f"Decision used ranking configuration {audit_record.ranking_configuration.version}.",
            f"Selected candidate confidence is {selected_input.confidence_status} from {selected_input.eligible_evaluation_count} certified evaluation(s).",
        )

        return AdaptiveDecisionExplanation(
            selected_model_id=audit_record.selected_model_id,
            selected_registry_id=selected_input.registry_id,
            selected_model_name=selected_input.model_name,
            selected_model_version=selected_input.model_version,
            selection_summary=summary,
            alternatives_considered=ordered_alternatives,
            candidates=tuple(explanations),
            ranking_configuration_version=audit_record.ranking_configuration.version,
            created_at=audit_record.created_at,
        )
