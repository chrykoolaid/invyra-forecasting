from __future__ import annotations

from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from invyra_forecasting.api.app import app
from invyra_forecasting.monitoring import (
    ForecastMonitoringEvent,
    ForecastMonitoringService,
    InMemoryForecastMonitoringRepository,
    MonitoringHealthStatus,
)


client = TestClient(app)


def test_phase_6g_monitoring_snapshot_summarizes_forecast_observability() -> None:
    service = ForecastMonitoringService(
        InMemoryForecastMonitoringRepository(
            (
                ForecastMonitoringEvent("event-1", "forecast", model_id="model-a", confidence=0.91, latency_ms=10.0),
                ForecastMonitoringEvent("event-2", "forecast", model_id="model-a", confidence=0.72, latency_ms=20.0),
                ForecastMonitoringEvent("event-3", "forecast", model_id="model-b", confidence=0.42, latency_ms=30.0),
            )
        )
    )

    snapshot = service.snapshot()

    assert snapshot.forecast_count == 3
    assert snapshot.successful_forecasts == 3
    assert snapshot.failed_forecasts == 0
    assert snapshot.average_latency_ms == 20.0
    assert snapshot.average_confidence == 0.6833
    assert snapshot.confidence_distribution == {"low": 1, "medium": 1, "high": 1}
    assert snapshot.model_usage == {"model-a": 2, "model-b": 1}
    assert snapshot.health_status == MonitoringHealthStatus.HEALTHY
    assert snapshot.advisory_only is True
    assert snapshot.read_only is True


def test_phase_6g_monitoring_snapshot_detects_degraded_state() -> None:
    service = ForecastMonitoringService(
        InMemoryForecastMonitoringRepository(
            (
                ForecastMonitoringEvent("event-1", "forecast", model_id="model-a", confidence=0.91, latency_ms=10.0, success=False),
                ForecastMonitoringEvent("event-2", "drift", model_id="model-a", drift_severity="CRITICAL"),
            )
        )
    )

    snapshot = service.snapshot()

    assert snapshot.health_status == MonitoringHealthStatus.DEGRADED
    assert snapshot.failed_forecasts == 1
    assert snapshot.drift_counts["CRITICAL"] == 1
    assert len(snapshot.warnings) == 2


def test_phase_6g_monitoring_snapshot_detects_watch_state() -> None:
    service = ForecastMonitoringService(
        InMemoryForecastMonitoringRepository((ForecastMonitoringEvent("event-1", "drift", drift_severity="WATCH"),))
    )

    snapshot = service.snapshot()

    assert snapshot.health_status == MonitoringHealthStatus.WATCH
    assert snapshot.drift_counts["WATCH"] == 1


def test_phase_6g_rejects_invalid_monitoring_events() -> None:
    with pytest.raises(ValueError, match="confidence must be between"):
        ForecastMonitoringEvent("event-1", "forecast", confidence=1.5)

    with pytest.raises(ValueError, match="latency_ms must be"):
        ForecastMonitoringEvent("event-1", "forecast", latency_ms=-1.0)

    event = ForecastMonitoringEvent("event-1", "forecast")
    with pytest.raises(ValueError, match="monitoring events must remain advisory-only"):
        replace(event, advisory_only=False)


def test_phase_6g_rejects_duplicate_monitoring_events() -> None:
    repository = InMemoryForecastMonitoringRepository()
    repository.record(ForecastMonitoringEvent("event-1", "forecast"))

    with pytest.raises(ValueError, match="monitoring event already recorded"):
        repository.record(ForecastMonitoringEvent("event-1", "forecast"))


def test_phase_6g_monitoring_api_returns_read_only_summary() -> None:
    response = client.get("/v1/monitoring/summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["api_version"] == "v1"
    assert payload["resource"] == "forecast_monitoring_summary"
    assert payload["advisory_only"] is True
    assert payload["read_only"] is True
    assert payload["inventory_source_of_truth_preserved"] is True
    assert payload["data"]["health_status"] == "HEALTHY"
    assert payload["data"]["forecast_count"] == 0


def test_phase_6g_metadata_lists_monitoring_endpoint() -> None:
    response = client.get("/v1")

    assert response.status_code == 200
    assert "/v1/monitoring/summary" in response.json()["data"]["stable_resources"]
