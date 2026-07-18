from dataclasses import fields, is_dataclass

from invyra_forecasting.api.decision_review_routes import router
from invyra_forecasting.decision_context import DecisionContext, DecisionContextService
from invyra_forecasting.decision_explanation import DecisionExplanation, DecisionExplanationService
from invyra_forecasting.decision_priority import DecisionPriorityAssessment, DecisionPriorityPolicy


PROHIBITED_DECISION_INTELLIGENCE_METHODS = {
    "recommend",
    "rank",
    "score",
    "select",
    "predict",
    "recalculate",
    "infer_inventory",
    "mutate_inventory",
    "mutate_stock",
    "create_stock_movement",
    "create_purchase_order",
    "approve_purchase_order",
    "update_history",
    "delete_history",
    "write_evidence",
}


def test_program_i_contracts_remain_immutable_and_governed() -> None:
    for contract in (
        DecisionContext,
        DecisionPriorityAssessment,
        DecisionExplanation,
    ):
        assert is_dataclass(contract)
        assert contract.__dataclass_params__.frozen is True
        names = {field.name for field in fields(contract)}
        assert {"advisory_only", "read_only", "inventory_source_of_truth_preserved"} <= names
        assert {"namespace", "as_of_utc", "evidence_refs", "history_refs"} <= names


def test_program_i_services_expose_no_recommendation_prediction_or_operational_actions() -> None:
    for service in (
        DecisionContextService,
        DecisionPriorityPolicy,
        DecisionExplanationService,
    ):
        exposed = {name for name in dir(service) if not name.startswith("_")}
        assert not (exposed & PROHIBITED_DECISION_INTELLIGENCE_METHODS)


def test_program_i_service_surfaces_remain_narrow_and_deterministic() -> None:
    assert {
        name for name in dir(DecisionContextService) if not name.startswith("_")
    } == {"compose"}
    assert {
        name for name in dir(DecisionPriorityPolicy) if not name.startswith("_")
    } == {"assess"}
    assert {
        name for name in dir(DecisionExplanationService) if not name.startswith("_")
    } == {"explain"}


def test_decision_review_api_remains_get_only_and_singular() -> None:
    decision_routes = {
        route.path: set(route.methods or ())
        for route in router.routes
        if route.path.startswith("/v1/intelligence/decisions/")
    }
    assert decision_routes == {
        "/v1/intelligence/decisions/review": {"GET"},
    }


def test_decision_intelligence_contracts_do_not_expose_execution_fields() -> None:
    prohibited_fields = {
        "recommended_action",
        "selected_model",
        "purchase_order",
        "stock_movement",
        "inventory_mutation",
        "auto_execute",
        "approval",
    }
    for contract in (
        DecisionContext,
        DecisionPriorityAssessment,
        DecisionExplanation,
    ):
        assert not ({field.name for field in fields(contract)} & prohibited_fields)
