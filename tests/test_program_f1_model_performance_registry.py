from __future__ import annotations

from contextlib import contextmanager
from dataclasses import FrozenInstanceError

import pytest

from invyra_forecasting.api import tenant_context
from invyra_forecasting.model_performance_registry import (
    InMemoryModelPerformanceRegistry,
    JsonlModelPerformanceRegistry,
    ModelLifecycleStatus,
    ModelPerformanceRegistryEntry,
    ModelPerformanceRegistryService,
)


@contextmanager
def _tenant(tenant_id: str | None):
    token = tenant_context._TENANT_ID.set(
        tenant_context.normalize_tenant_id(tenant_id)
    )
    try:
        yield
    finally:
        tenant_context._TENANT_ID.reset(token)


def _register(
    service: ModelPerformanceRegistryService,
    *,
    registry_id: str = "registry-1",
    model_name: str = "seasonal-naive",
    model_version: str = "1.0",
):
    return service.register(
        registry_id=registry_id,
        model_name=model_name,
        model_version=model_version,
        lifecycle_status=ModelLifecycleStatus.ACTIVE,
        supported_forecast_horizons=(28, 7, 14, 7),
        supported_demand_profiles=("seasonal", "stable", "seasonal"),
        registered_at_utc="2026-07-15T16:00:00+00:00",
    )


def test_registers_normalized_immutable_model_metadata() -> None:
    service = ModelPerformanceRegistryService()

    entry = _register(service)

    assert entry.model_name == "seasonal-naive"
    assert entry.model_version == "1.0"
    assert entry.lifecycle_status is ModelLifecycleStatus.ACTIVE
    assert entry.supported_forecast_horizons == (7, 14, 28)
    assert entry.supported_demand_profiles == ("seasonal", "stable")
    assert service.get("registry-1") == entry
    with pytest.raises(FrozenInstanceError):
        entry.model_version = "2.0"


def test_rejects_duplicate_model_version_and_registry_id() -> None:
    service = ModelPerformanceRegistryService()
    _register(service)

    with pytest.raises(ValueError, match="model version already registered"):
        _register(service, registry_id="registry-2")

    with pytest.raises(ValueError, match="model registry entry already exists"):
        _register(
            service,
            registry_id="registry-1",
            model_name="croston",
            model_version="1.0",
        )


def test_supports_historical_versions_without_updates_or_deletes() -> None:
    service = ModelPerformanceRegistryService()
    first = _register(service)
    second = _register(
        service,
        registry_id="registry-2",
        model_version="2.0",
    )

    assert service.for_model("seasonal-naive") == (first, second)
    assert not hasattr(service, "update")
    assert not hasattr(service, "delete")


def test_validates_lifecycle_horizons_profiles_and_guardrails() -> None:
    with pytest.raises(ValueError, match="positive integers"):
        ModelPerformanceRegistryService().register(
            model_name="baseline",
            model_version="1.0",
            lifecycle_status=ModelLifecycleStatus.EXPERIMENTAL,
            supported_forecast_horizons=(0,),
        )

    with pytest.raises(ValueError, match="non-empty strings"):
        ModelPerformanceRegistryService().register(
            model_name="baseline",
            model_version="1.0",
            lifecycle_status=ModelLifecycleStatus.EXPERIMENTAL,
            supported_forecast_horizons=(7,),
            supported_demand_profiles=("",),
        )

    with pytest.raises(ValueError, match="advisory-only and read-only"):
        ModelPerformanceRegistryEntry(
            registry_id="bad",
            model_name="baseline",
            model_version="1.0",
            lifecycle_status=ModelLifecycleStatus.ACTIVE,
            supported_forecast_horizons=(7,),
            supported_demand_profiles=(),
            namespace="default",
            advisory_only=False,
        )


def test_serialization_and_restart_reconstruction_are_compatible(tmp_path) -> None:
    path = tmp_path / "model-registry.jsonl"
    service = ModelPerformanceRegistryService(JsonlModelPerformanceRegistry(path))
    original = _register(service)

    restarted = ModelPerformanceRegistryService(JsonlModelPerformanceRegistry(path))
    loaded = restarted.get("registry-1")

    assert loaded == original
    assert loaded.to_dict()["lifecycle_status"] == "active"
    assert loaded.to_dict()["supported_forecast_horizons"] == [7, 14, 28]
    assert loaded.advisory_only is True
    assert loaded.read_only is True
    assert loaded.inventory_source_of_truth_preserved is True


def test_registry_is_tenant_isolated_in_memory_and_after_restart(tmp_path) -> None:
    path = tmp_path / "model-registry.jsonl"

    with _tenant("alpha"):
        _register(
            ModelPerformanceRegistryService(JsonlModelPerformanceRegistry(path)),
            registry_id="shared-id",
        )

    with _tenant("bravo"):
        service = ModelPerformanceRegistryService(JsonlModelPerformanceRegistry(path))
        assert service.get("shared-id") is None
        _register(service, registry_id="shared-id")

    with _tenant("alpha"):
        records = ModelPerformanceRegistryService(
            JsonlModelPerformanceRegistry(path)
        ).all()
        assert len(records) == 1
        assert records[0].namespace == "alpha"

    with _tenant("bravo"):
        records = ModelPerformanceRegistryService(
            JsonlModelPerformanceRegistry(path)
        ).all()
        assert len(records) == 1
        assert records[0].namespace == "bravo"


def test_f1_exposes_metadata_only_and_does_not_score_or_select_models() -> None:
    entry = _register(ModelPerformanceRegistryService())
    payload = entry.to_dict()

    forbidden = {
        "accuracy",
        "bias",
        "calibration",
        "confidence_score",
        "ranking_score",
        "rank",
        "weight",
        "selected",
    }
    assert forbidden.isdisjoint(payload)
    assert not hasattr(InMemoryModelPerformanceRegistry(), "select")
    assert not hasattr(InMemoryModelPerformanceRegistry(), "rank")
