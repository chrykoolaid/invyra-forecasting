from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from invyra_forecasting.decision_context import DecisionContext
from invyra_forecasting.decision_priority import DecisionPriorityAssessment

DECISION_EXPLANATION_SCHEMA_VERSION = "1.0.0"


@dataclass(frozen=True)
class DecisionExplanation:
    namespace: str
    as_of_utc: str
    priority: str
    headline: str
    summary: str
    contributing_reason_codes: tuple[str, ...]
    contributing_reasons: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    history_refs: tuple[str, ...]
    schema_version: str = DECISION_EXPLANATION_SCHEMA_VERSION
    advisory_only: bool = True
    read_only: bool = True
    inventory_source_of_truth_preserved: bool = True

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["contributing_reason_codes"] = list(self.contributing_reason_codes)
        payload["contributing_reasons"] = list(self.contributing_reasons)
        payload["evidence_refs"] = list(self.evidence_refs)
        payload["history_refs"] = list(self.history_refs)
        return payload


class DecisionExplanationService:
    """Explains certified decision context and priority without changing policy outcomes."""

    def explain(
        self,
        context: DecisionContext,
        priority: DecisionPriorityAssessment,
    ) -> DecisionExplanation:
        _validate_inputs(context, priority)
        level = priority.priority.value
        return DecisionExplanation(
            namespace=context.namespace,
            as_of_utc=context.as_of_utc,
            priority=level,
            headline=f"Decision review priority: {level}.",
            summary=_summary(level, priority.reasons),
            contributing_reason_codes=priority.reason_codes,
            contributing_reasons=priority.reasons,
            evidence_refs=context.evidence_refs,
            history_refs=context.history_refs,
        )


def _summary(level: str, reasons: tuple[str, ...]) -> str:
    joined = " ".join(reasons)
    if joined:
        return f"The fixed decision-priority policy assigned {level} because: {joined}"
    return f"The fixed decision-priority policy assigned {level} with no additional contributing condition."


def _validate_inputs(
    context: DecisionContext,
    priority: DecisionPriorityAssessment,
) -> None:
    if context.namespace != priority.namespace:
        raise ValueError("decision explanation inputs must belong to the same tenant namespace")
    if context.as_of_utc != priority.as_of_utc:
        raise ValueError("decision explanation inputs must use the same as_of_utc boundary")
    if tuple(context.evidence_refs) != tuple(priority.evidence_refs):
        raise ValueError("decision priority evidence references must match the decision context")
    if tuple(context.history_refs) != tuple(priority.history_refs):
        raise ValueError("decision priority history references must match the decision context")
    guarded = (context, priority)
    if any(not item.advisory_only or not item.read_only for item in guarded):
        raise ValueError("decision explanation inputs must remain advisory-only and read-only")
    if any(not item.inventory_source_of_truth_preserved for item in guarded):
        raise ValueError("inventory source of truth must be preserved")
