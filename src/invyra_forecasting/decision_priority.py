from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

from invyra_forecasting.decision_context import DecisionContext

DECISION_PRIORITY_SCHEMA_VERSION = "1.0.0"


class DecisionPriorityLevel(str, Enum):
    INFORMATIONAL = "informational"
    NORMAL = "normal"
    WATCH = "watch"
    HIGH = "high"


@dataclass(frozen=True)
class DecisionPriorityAssessment:
    namespace: str
    as_of_utc: str
    priority: DecisionPriorityLevel
    reason_codes: tuple[str, ...]
    reasons: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    history_refs: tuple[str, ...]
    schema_version: str = DECISION_PRIORITY_SCHEMA_VERSION
    advisory_only: bool = True
    read_only: bool = True
    inventory_source_of_truth_preserved: bool = True

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["priority"] = self.priority.value
        payload["reason_codes"] = list(self.reason_codes)
        payload["reasons"] = list(self.reasons)
        payload["evidence_refs"] = list(self.evidence_refs)
        payload["history_refs"] = list(self.history_refs)
        return payload


class DecisionPriorityPolicy:
    """Applies fixed, explainable precedence rules without scoring or recommending action."""

    def assess(self, context: DecisionContext) -> DecisionPriorityAssessment:
        _validate_context(context)
        conditions = _conditions(context)
        priority = _priority(conditions)
        selected = tuple(condition for condition in conditions if condition[0] == priority)
        if not selected:
            selected = ((priority, f"{priority.value}_state", _default_reason(priority)),)

        return DecisionPriorityAssessment(
            namespace=context.namespace,
            as_of_utc=context.as_of_utc,
            priority=priority,
            reason_codes=tuple(code for _, code, _ in selected),
            reasons=tuple(reason for _, _, reason in selected),
            evidence_refs=context.evidence_refs,
            history_refs=context.history_refs,
        )


def _conditions(context: DecisionContext) -> tuple[tuple[DecisionPriorityLevel, str, str], ...]:
    conditions: list[tuple[DecisionPriorityLevel, str, str]] = []

    for signal in context.enterprise_risks.signals:
        severity = _value(signal.severity)
        if severity == "elevated":
            conditions.append((DecisionPriorityLevel.HIGH, f"enterprise_{_value(signal.risk_type)}", signal.reason))
        elif severity == "watch":
            conditions.append((DecisionPriorityLevel.WATCH, f"enterprise_{_value(signal.risk_type)}", signal.reason))
        else:
            conditions.append((DecisionPriorityLevel.INFORMATIONAL, f"enterprise_{_value(signal.risk_type)}", signal.reason))

    coverage = _value(context.operational_coverage.status)
    if coverage == "limited":
        conditions.append((DecisionPriorityLevel.HIGH, "operational_limited_coverage", "Operational evidence linkage coverage is limited."))
    elif coverage == "developing":
        conditions.append((DecisionPriorityLevel.WATCH, "operational_developing_coverage", "Operational evidence linkage coverage is developing."))
    elif coverage == "unavailable":
        conditions.append((DecisionPriorityLevel.INFORMATIONAL, "operational_coverage_unavailable", "Operational evidence linkage coverage is unavailable."))

    for signal in context.operational_evidence_signals.signals:
        level = DecisionPriorityLevel.WATCH if _value(signal.severity) == "watch" else DecisionPriorityLevel.INFORMATIONAL
        conditions.append((level, f"operational_{signal.code}", signal.reason))

    return tuple(conditions)


def _priority(conditions: tuple[tuple[DecisionPriorityLevel, str, str], ...]) -> DecisionPriorityLevel:
    levels = {condition[0] for condition in conditions}
    for candidate in (
        DecisionPriorityLevel.HIGH,
        DecisionPriorityLevel.WATCH,
        DecisionPriorityLevel.INFORMATIONAL,
    ):
        if candidate in levels:
            return candidate
    return DecisionPriorityLevel.NORMAL


def _default_reason(priority: DecisionPriorityLevel) -> str:
    if priority is DecisionPriorityLevel.NORMAL:
        return "No certified condition requires elevated review attention."
    return "Certified evidence provides contextual information for human review."


def _value(value: Any) -> str:
    return str(getattr(value, "value", value))


def _validate_context(context: DecisionContext) -> None:
    if not context.namespace:
        raise ValueError("decision context namespace is required")
    if not context.advisory_only or not context.read_only:
        raise ValueError("decision priority input must remain advisory-only and read-only")
    if not context.inventory_source_of_truth_preserved:
        raise ValueError("inventory source of truth must be preserved")
