from dataclasses import FrozenInstanceError
from types import SimpleNamespace

import pytest

from invyra_forecasting.decision_priority import (
    DecisionPriorityLevel,
    DecisionPriorityPolicy,
)


def _context(*, risks=(), coverage="complete", operational_signals=(), **changes):
    values = {
        "namespace": "tenant-a",
        "as_of_utc": "2026-07-31T00:00:00+00:00",
        "enterprise_risks": SimpleNamespace(signals=risks),
        "operational_coverage": SimpleNamespace(status=coverage),
        "operational_evidence_signals": SimpleNamespace(signals=operational_signals),
        "evidence_refs": ("eval-1",),
        "history_refs": ("history-1",),
        "advisory_only": True,
        "read_only": True,
        "inventory_source_of_truth_preserved": True,
    }
    values.update(changes)
    return SimpleNamespace(**values)


def _risk(severity, risk_type="weak_accuracy", reason="Certified accuracy is below threshold."):
    return SimpleNamespace(severity=severity, risk_type=risk_type, reason=reason)


def _signal(severity, code="incomplete_evidence_linkage", reason="Evidence linkage is incomplete."):
    return SimpleNamespace(severity=severity, code=code, reason=reason)


def test_elevated_enterprise_condition_produces_high_priority() -> None:
    result = DecisionPriorityPolicy().assess(_context(risks=(_risk("elevated"),)))
    assert result.priority is DecisionPriorityLevel.HIGH
    assert result.reason_codes == ("enterprise_weak_accuracy",)


def test_limited_operational_coverage_produces_high_priority() -> None:
    result = DecisionPriorityPolicy().assess(_context(coverage="limited"))
    assert result.priority is DecisionPriorityLevel.HIGH
    assert result.reason_codes == ("operational_limited_coverage",)


def test_watch_condition_takes_precedence_over_informational_condition() -> None:
    result = DecisionPriorityPolicy().assess(
        _context(
            risks=(_risk("informational", "no_evidence", "No evidence."),),
            operational_signals=(_signal("watch"),),
        )
    )
    assert result.priority is DecisionPriorityLevel.WATCH
    assert result.reason_codes == ("operational_incomplete_evidence_linkage",)


def test_only_informational_conditions_remain_informational() -> None:
    result = DecisionPriorityPolicy().assess(
        _context(coverage="unavailable", operational_signals=(_signal("informational", "no_history", "No history."),))
    )
    assert result.priority is DecisionPriorityLevel.INFORMATIONAL
    assert result.reason_codes == (
        "operational_coverage_unavailable",
        "operational_no_history",
    )


def test_no_conditions_produce_normal_priority() -> None:
    result = DecisionPriorityPolicy().assess(_context())
    assert result.priority is DecisionPriorityLevel.NORMAL
    assert result.reason_codes == ("normal_state",)


def test_assessment_is_immutable_and_serialization_is_defensive() -> None:
    result = DecisionPriorityPolicy().assess(_context())
    with pytest.raises(FrozenInstanceError):
        result.priority = DecisionPriorityLevel.HIGH
    payload = result.to_dict()
    payload["evidence_refs"].append("changed")
    assert result.evidence_refs == ("eval-1",)
    assert payload["priority"] == "normal"


def test_non_governed_context_is_rejected() -> None:
    with pytest.raises(ValueError, match="advisory-only and read-only"):
        DecisionPriorityPolicy().assess(_context(read_only=False))


def test_inventory_source_of_truth_guard_is_enforced() -> None:
    with pytest.raises(ValueError, match="source of truth"):
        DecisionPriorityPolicy().assess(_context(inventory_source_of_truth_preserved=False))


def test_policy_surface_remains_assessment_only() -> None:
    exposed = {name for name in dir(DecisionPriorityPolicy) if not name.startswith("_")}
    assert exposed == {"assess"}
