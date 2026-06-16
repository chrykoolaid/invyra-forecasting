import pytest

from invyra_forecasting.integrations import get_module_contract, list_module_contracts, validate_module_contract


EXPECTED_MODULES = {"inventory", "scanops", "reorder_review", "dashboard", "reports"}


def test_all_expected_module_contracts_are_registered():
    contracts = list_module_contracts()
    names = {contract["module_name"] for contract in contracts}
    assert names == EXPECTED_MODULES


def test_registered_contracts_pass_validation():
    for module_name in EXPECTED_MODULES:
        contract = get_module_contract(module_name)
        assert validate_module_contract(contract) == []


def test_contracts_preserve_advisory_and_environment_governance():
    for module_name in EXPECTED_MODULES:
        contract = get_module_contract(module_name)
        endpoint_rules = " ".join(rule for endpoint in contract.endpoints for rule in endpoint.governance_rules)
        assert "advisory" in endpoint_rules.lower()
        assert "environment" in endpoint_rules.lower()
        assert any("environment" in item.lower() for item in contract.must_send)


def test_reorder_review_blocks_auto_purchase_in_contract():
    contract = get_module_contract("reorder_review")
    joined = " ".join(contract.must_not_do + [rule for endpoint in contract.endpoints for rule in endpoint.governance_rules])
    assert "Auto-approve" in joined or "automatically create" in joined
    assert "purchase" in joined.lower()


def test_unknown_contract_name_raises_key_error():
    with pytest.raises(KeyError):
        get_module_contract("unknown_module")
