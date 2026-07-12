from __future__ import annotations

from contextlib import contextmanager

from invyra_forecasting.api import tenant_context
from invyra_forecasting.monitoring import (
    ForecastMonitoringEvent,
    ForecastMonitoringService,
    InMemoryForecastMonitoringRepository,
)


@contextmanager
def _tenant(tenant_id: str | None):
    token = tenant_context._TENANT_ID.set(tenant_context.normalize_tenant_id(tenant_id))
    try:
        yield
    finally:
        tenant_context._TENANT_ID.reset(token)


def _event(event_id: str, *, confidence: float, success: bool = True) -> ForecastMonitoringEvent:
    return ForecastMonitoringEvent(
        event_id=event_id,
        event_type="forecast",
        model_id="seasonal-naive",
        confidence=confidence,
        latency_ms=12.0,
        success=success,
    )


def test_monitoring_events_are_isolated_by_namespace():
    repository = InMemoryForecastMonitoringRepository()
    service = ForecastMonitoringService(repository)

    with _tenant("alpha"):
        service.record_event(_event("shared-id", confidence=0.9))
        alpha = service.snapshot()

    with _tenant("bravo"):
        service.record_event(_event("shared-id", confidence=0.4, success=False))
        bravo = service.snapshot()

    assert alpha.forecast_count == 1
    assert alpha.successful_forecasts == 1
    assert alpha.failed_forecasts == 0
    assert alpha.average_confidence == 0.9

    assert bravo.forecast_count == 1
    assert bravo.successful_forecasts == 0
    assert bravo.failed_forecasts == 1
    assert bravo.average_confidence == 0.4


def test_default_namespace_is_isolated_from_named_tenants():
    repository = InMemoryForecastMonitoringRepository()
    service = ForecastMonitoringService(repository)

    with _tenant(None):
        service.record_event(_event("default-event", confidence=0.8))
        assert service.snapshot().forecast_count == 1

    with _tenant("alpha"):
        assert service.snapshot().forecast_count == 0

    with _tenant(None):
        assert service.snapshot().forecast_count == 1


def test_duplicate_event_ids_are_rejected_only_within_same_namespace():
    repository = InMemoryForecastMonitoringRepository()

    with _tenant("alpha"):
        repository.record(_event("duplicate", confidence=0.7))
        try:
            repository.record(_event("duplicate", confidence=0.7))
        except ValueError as exc:
            assert str(exc) == "monitoring event already recorded: duplicate"
        else:
            raise AssertionError("duplicate event should be rejected within one namespace")

    with _tenant("bravo"):
        repository.record(_event("duplicate", confidence=0.7))
        assert len(repository.all()) == 1


def test_namespace_switching_does_not_change_snapshot_calculation():
    repository = InMemoryForecastMonitoringRepository()
    service = ForecastMonitoringService(repository)

    for tenant_id in ("alpha", "bravo"):
        with _tenant(tenant_id):
            service.record_event(_event(f"{tenant_id}-1", confidence=0.6))
            service.record_event(_event(f"{tenant_id}-2", confidence=0.8))

    with _tenant("alpha"):
        alpha = service.snapshot().to_dict()

    with _tenant("bravo"):
        bravo = service.snapshot().to_dict()

    assert alpha == bravo
