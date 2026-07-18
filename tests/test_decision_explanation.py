from dataclasses import FrozenInstanceError
from types import SimpleNamespace

import pytest

from invyra_forecasting.decision_explanation import DecisionExplanationService


class _PriorityValue:
    value = "watch"


def _context(**changes):
    values = {
        "namespace": "tenant-a",
        "as_of_utc": "2026-07-31T00:00:00+00:00",
        "evidence_refs": ("eval-1", "eval-2"),
        "history_refs": ("history-1",),
        "advisory_only": True,
        "read_only": True,
        "inventory_source_of_truth_preserved": True,
    }
    values.update(changes)
    return SimpleNamespace(**values)


def _priority(**changes):
    values = {
        "namespace": "tenant-a",
        "as_of_utc": "2026-07-31T00:00:00+00:00",
        "priority": _PriorityValue(),
        "reason_codes": ("operational_developing_coverage",),
        "reasons": ("Operational evidence linkage coverage is developing.",),
        "evidence_refs": ("eval-1", "eval-2"),
        "history_refs": ("history-1",),
        "advisory_only": True,
        "read_only": True,
        "inventory_source_of_truth_preserved": True,
    }
    values.update(changes)
    return SimpleNamespace(**values)


def test_explain_preserves_priority_rationale_and_refs() -> None:
    result = DecisionExplanationService().explain(_context(), _priority())
    assert result.priority == "watch"
    assert result.headline == "Decision review priority: watch."
    assert result.contributing_reason_codes == ("operational_developing_coverage",)
    assert "fixed decision-priority policy" in result.summary
    assert result.evidence_refs == ("eval-1", "eval-2")
    assert result.history_refs == ("history-1",)
    assert result.advisory_only is True
    assert result.read_only is True


def test_explanation_is_immutable_and_serialization_is_defensive() -> None:
    result = DecisionExplanationService().explain(_context(), _priority())
    with pytest.raises(FrozenInstanceError):
        result.priority = "high"
    payload = result.to_dict()
    payload["evidence_refs"].append("changed")
    assert "changed" not in result.evidence_refs


def test_mismatched_tenant_is_rejected() -> None:
    with pytest.raises(ValueError, match="same tenant namespace"):
        DecisionExplanationService().explain(_context(), _priority(namespace="tenant-b"))


def test_mismatched_timestamp_is_rejected() -> None:
    with pytest.raises(ValueError, match="same as_of_utc"):
        DecisionExplanationService().explain(
            _context(),
            _priority(as_of_utc="2026-08-01T00:00:00+00:00"),
        )


def test_reference_drift_is_rejected() -> None:
    with pytest.raises(ValueError, match="evidence references"):
        DecisionExplanationService().explain(
            _context(),
            _priority(evidence_refs=("different",)),
        )


def test_non_governed_input_is_rejected() -> None:
    with pytest.raises(ValueError, match="advisory-only and read-only"):
        DecisionExplanationService().explain(_context(), _priority(read_only=False))


def test_service_surface_remains_explanation_only() -> None:
    exposed = {name for name in dir(DecisionExplanationService) if not name.startswith("_")}
    assert exposed == {"explain"}
