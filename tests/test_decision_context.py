from dataclasses import FrozenInstanceError
from types import SimpleNamespace

import pytest

from invyra_forecasting.decision_context import DecisionContextService


class _Input(SimpleNamespace):
    def to_dict(self):
        return dict(self.payload)


def _base(**changes):
    values = {
        "namespace": "tenant-a",
        "as_of_utc": "2026-07-31T00:00:00+00:00",
        "advisory_only": True,
        "read_only": True,
        "inventory_source_of_truth_preserved": True,
        "payload": {"source": "certified"},
    }
    values.update(changes)
    return _Input(**values)


def _inputs():
    enterprise_summary = _base()
    enterprise_health = _base(evidence_refs=("eval-2", "eval-1"))
    enterprise_risks = _base(
        signals=(
            _Input(evidence_refs=("eval-3",)),
        )
    )
    operational_summary = _base(
        evidence_refs=("eval-4",),
        history_refs=("history-2", "history-1"),
    )
    operational_coverage = _base(
        evidence_refs=("eval-4", "eval-5"),
        history_refs=("history-1", "history-3"),
    )
    operational_signals = _base(
        signals=(
            _Input(evidence_refs=("eval-6",), history_refs=("history-4",)),
        )
    )
    return (
        enterprise_summary,
        enterprise_health,
        enterprise_risks,
        operational_summary,
        operational_coverage,
        operational_signals,
    )


def test_compose_preserves_certified_sections_and_consolidates_refs() -> None:
    result = DecisionContextService().compose(*_inputs())
    assert result.namespace == "tenant-a"
    assert result.evidence_refs == (
        "eval-1",
        "eval-2",
        "eval-3",
        "eval-4",
        "eval-5",
        "eval-6",
    )
    assert result.history_refs == (
        "history-1",
        "history-2",
        "history-3",
        "history-4",
    )
    assert result.advisory_only is True
    assert result.read_only is True
    assert result.inventory_source_of_truth_preserved is True


def test_context_is_immutable_and_serialization_is_defensive() -> None:
    result = DecisionContextService().compose(*_inputs())
    with pytest.raises(FrozenInstanceError):
        result.namespace = "changed"
    payload = result.to_dict()
    payload["evidence_refs"].append("changed")
    assert "changed" not in result.evidence_refs
    assert payload["enterprise_summary"] == {"source": "certified"}


def test_mismatched_tenant_is_rejected() -> None:
    inputs = list(_inputs())
    inputs[-1] = _base(namespace="tenant-b", signals=())
    with pytest.raises(ValueError, match="same tenant namespace"):
        DecisionContextService().compose(*inputs)


def test_mismatched_timestamp_is_rejected() -> None:
    inputs = list(_inputs())
    inputs[-1] = _base(as_of_utc="2026-08-01T00:00:00+00:00", signals=())
    with pytest.raises(ValueError, match="same as_of_utc"):
        DecisionContextService().compose(*inputs)


def test_non_governed_input_is_rejected() -> None:
    inputs = list(_inputs())
    inputs[-1] = _base(read_only=False, signals=())
    with pytest.raises(ValueError, match="advisory-only and read-only"):
        DecisionContextService().compose(*inputs)


def test_service_surface_remains_composition_only() -> None:
    exposed = {name for name in dir(DecisionContextService) if not name.startswith("_")}
    assert exposed == {"compose"}
