from __future__ import annotations

import pytest

from invyra_forecasting.models import (
    ModelCompatibilityProfile,
    ModelGovernanceEventType,
    ModelLifecycleStatus,
    ModelRegistryEntryV2,
    ModelRegistryV2,
)


def _entry(model_id: str, version: str, *, status: ModelLifecycleStatus = ModelLifecycleStatus.TESTING) -> ModelRegistryEntryV2:
    return ModelRegistryEntryV2(
        model_id=model_id,
        model_name="demand_model",
        model_version=version,
        status=status,
        activated_at_utc="2026-07-05T00:00:00+00:00" if status == ModelLifecycleStatus.PRODUCTION else None,
        compatibility=ModelCompatibilityProfile(
            forecast_types=("item_location_demand",),
            horizons_days=(30, 60),
            signal_types=("sales", "stock_movement"),
        ),
    )


def test_phase_6c_registers_models_and_records_governance_events() -> None:
    registry = ModelRegistryV2()
    entry = registry.register(_entry("demand::1", "1.0"), reason="initial registration")

    assert registry.get("demand::1") == entry
    events = registry.events("demand::1")
    assert len(events) == 1
    assert events[0].event_type == ModelGovernanceEventType.REGISTERED
    assert events[0].new_status == ModelLifecycleStatus.TESTING
    assert events[0].advisory_only is True


def test_phase_6c_activates_and_retires_model_versions() -> None:
    registry = ModelRegistryV2((_entry("demand::1", "1.0"),))

    activated = registry.activate("demand::1", reason="approved for production")
    retired = registry.retire("demand::1", reason="superseded")

    assert activated.status == ModelLifecycleStatus.PRODUCTION
    assert activated.activated_at_utc is not None
    assert retired.status == ModelLifecycleStatus.RETIRED
    assert retired.retired_at_utc is not None
    assert [event.event_type for event in registry.events("demand::1")] == [
        ModelGovernanceEventType.REGISTERED,
        ModelGovernanceEventType.ACTIVATED,
        ModelGovernanceEventType.RETIRED,
    ]


def test_phase_6c_tracks_version_history_and_compatible_models() -> None:
    registry = ModelRegistryV2(
        (
            _entry("demand::1", "1.0", status=ModelLifecycleStatus.PRODUCTION),
            _entry("demand::2", "2.0", status=ModelLifecycleStatus.APPROVED),
            _entry("demand::3", "3.0", status=ModelLifecycleStatus.TESTING),
        )
    )

    history = registry.version_history("demand_model")
    compatible = registry.compatible(forecast_type="item_location_demand", forecast_days=30)

    assert [entry.model_version for entry in history] == ["1.0", "2.0", "3.0"]
    assert [entry.model_id for entry in compatible] == ["demand::1", "demand::2"]


def test_phase_6c_rejects_invalid_registry_entries() -> None:
    with pytest.raises(ValueError, match="model_id is required"):
        ModelRegistryEntryV2(model_id="", model_name="model", model_version="1.0")

    with pytest.raises(ValueError, match="production models must include activated_at_utc"):
        ModelRegistryEntryV2(
            model_id="model::1",
            model_name="model",
            model_version="1.0",
            status=ModelLifecycleStatus.PRODUCTION,
        )

    with pytest.raises(ValueError, match="model registry entries must remain advisory-only"):
        ModelRegistryEntryV2(model_id="model::1", model_name="model", model_version="1.0", advisory_only=False)


def test_phase_6c_validation_flags_missing_replacement_model() -> None:
    registry = ModelRegistryV2(
        (
            ModelRegistryEntryV2(
                model_id="demand::2",
                model_name="demand_model",
                model_version="2.0",
                replaces_model_id="demand::missing",
            ),
        )
    )

    assert registry.validate() == ("demand::2 replaces missing model demand::missing",)


def test_phase_6c_retired_models_cannot_be_activated() -> None:
    registry = ModelRegistryV2((_entry("demand::1", "1.0"),))
    registry.retire("demand::1", reason="removed from use")

    with pytest.raises(ValueError, match="retired models cannot be activated"):
        registry.activate("demand::1")
