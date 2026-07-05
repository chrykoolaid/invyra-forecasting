import pytest

from invyra_forecasting.registry import ModelLifecycleRegistry, ModelLifecycleState, ModelRegistryEntry


def _entry(model_id: str = "baseline::2W.1") -> ModelRegistryEntry:
    return ModelRegistryEntry(
        model_id=model_id,
        model_name="baseline_explainable_demand_model",
        model_version="2W.1",
        forecast_type="item_location_demand",
        owner="Invyra",
        strengths=("deterministic", "explainable"),
        limitations=("not_ml",),
    )


def test_model_registry_entry_validates_required_fields():
    with pytest.raises(ValueError):
        ModelRegistryEntry(model_id="", model_name="model", model_version="1", forecast_type="item_location_demand")
    with pytest.raises(ValueError):
        ModelRegistryEntry(model_id="id", model_name="", model_version="1", forecast_type="item_location_demand")


def test_model_registry_entry_preserves_guardrails():
    with pytest.raises(ValueError):
        ModelRegistryEntry(
            model_id="id",
            model_name="model",
            model_version="1",
            forecast_type="item_location_demand",
            advisory_only=False,
        )


def test_model_lifecycle_valid_transition_records_history():
    entry = _entry()
    testing = entry.transition(ModelLifecycleState.TESTING, reason="begin test cycle")

    assert testing.lifecycle_state == ModelLifecycleState.TESTING
    assert len(testing.transition_history) == 1
    assert testing.transition_history[0].from_state == ModelLifecycleState.DRAFT
    assert testing.transition_history[0].to_state == ModelLifecycleState.TESTING


def test_model_lifecycle_rejects_invalid_transition():
    with pytest.raises(ValueError):
        _entry().transition(ModelLifecycleState.PRODUCTION, reason="skip validation")


def test_model_lifecycle_registry_duplicate_protection_and_lookup():
    registry = ModelLifecycleRegistry()
    entry = _entry()

    registry.register(entry)

    assert registry.get(entry.model_id) == entry
    with pytest.raises(ValueError):
        registry.register(entry)


def test_model_lifecycle_registry_transition_updates_entry():
    registry = ModelLifecycleRegistry()
    registry.register(_entry())

    testing = registry.transition("baseline::2W.1", ModelLifecycleState.TESTING, reason="testing")
    validation = registry.transition("baseline::2W.1", ModelLifecycleState.VALIDATION, reason="validation")

    assert testing.lifecycle_state == ModelLifecycleState.TESTING
    assert validation.lifecycle_state == ModelLifecycleState.VALIDATION
    assert len(validation.transition_history) == 2


def test_model_lifecycle_eligible_models_require_approved_or_production_state():
    registry = ModelLifecycleRegistry()
    registry.register(_entry("draft::1"))
    registry.register(
        _entry("approved::1")
        .transition(ModelLifecycleState.TESTING, reason="testing")
        .transition(ModelLifecycleState.VALIDATION, reason="validation")
        .transition(ModelLifecycleState.APPROVED, reason="approved")
    )

    eligible = registry.eligible(forecast_type="item_location_demand", forecast_horizon_days=30)

    assert len(eligible) == 1
    assert eligible[0].model_id == "approved::1"


def test_model_lifecycle_serialization_is_business_readable():
    entry = _entry().transition(ModelLifecycleState.TESTING, reason="testing")
    payload = entry.to_dict()

    assert payload["lifecycle_state"] == "TESTING"
    assert payload["supported_horizons_days"] == [7, 14, 30, 60, 90]
    assert payload["transition_history"][0]["reason"] == "testing"
