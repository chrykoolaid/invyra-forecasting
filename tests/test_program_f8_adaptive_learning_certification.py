from dataclasses import fields, is_dataclass

from invyra_forecasting.adaptive_decision_explainability import (
    AdaptiveDecisionExplainabilityService,
    AdaptiveDecisionExplanation,
)
from invyra_forecasting.adaptive_selection_inputs import AdaptiveSelectionInputBuilder
from invyra_forecasting.model_confidence_governance import ModelConfidenceGovernancePolicy
from invyra_forecasting.model_drift_detection import ModelDriftDetectionPolicy
from invyra_forecasting.model_performance_registry import (
    InMemoryModelPerformanceRegistry,
    ModelPerformanceRegistryEntry,
)
from invyra_forecasting.model_performance_statistics import ModelPerformanceStatisticsService
from invyra_forecasting.model_retirement_governance import (
    ModelRetirementGovernanceDecision,
    ModelRetirementGovernancePolicy,
)


PROHIBITED_AUTOMATION_METHODS = {
    "select",
    "rank",
    "score",
    "retrain",
    "tune",
    "retire",
    "disable",
    "mutate_inventory",
    "create_purchase_order",
}


def test_program_f_contracts_remain_immutable_and_advisory_only() -> None:
    for contract in (
        ModelPerformanceRegistryEntry,
        AdaptiveDecisionExplanation,
        ModelRetirementGovernanceDecision,
    ):
        assert is_dataclass(contract)
        params = contract.__dataclass_params__
        assert params.frozen is True
        names = {field.name for field in fields(contract)}
        assert {"advisory_only", "read_only", "inventory_source_of_truth_preserved"} <= names


def test_program_f_services_expose_no_automatic_learning_or_operational_actions() -> None:
    services = (
        ModelPerformanceStatisticsService,
        ModelConfidenceGovernancePolicy,
        AdaptiveSelectionInputBuilder,
        ModelDriftDetectionPolicy,
        ModelRetirementGovernancePolicy,
        AdaptiveDecisionExplainabilityService,
    )
    for service in services:
        exposed = {name for name in dir(service) if not name.startswith("_")}
        assert not (exposed & PROHIBITED_AUTOMATION_METHODS)


def test_model_registry_remains_append_only() -> None:
    repository = InMemoryModelPerformanceRegistry()
    exposed = {name for name in dir(repository) if not name.startswith("_")}
    assert "append" in exposed
    assert "update" not in exposed
    assert "delete" not in exposed
    assert "remove" not in exposed


def test_retirement_governance_requires_human_approval() -> None:
    field_defaults = {
        field.name: field.default
        for field in fields(ModelRetirementGovernanceDecision)
        if field.default is not field.default_factory
    }
    assert field_defaults["explicit_approval_required"] is True
    assert field_defaults["automatic_transition_permitted"] is False


def test_explainability_service_does_not_rescore_or_reselect() -> None:
    exposed = {
        name for name in dir(AdaptiveDecisionExplainabilityService)
        if not name.startswith("_")
    }
    assert exposed == {"explain"}
