from __future__ import annotations

from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from invyra_forecasting.api.app import app
from invyra_forecasting.performance import (
    InMemoryPerformanceBenchmarkRepository,
    PerformanceBenchmarkRecord,
    PerformanceBenchmarkService,
    PerformanceHealthStatus,
)


client = TestClient(app)


def test_phase_6h_summarizes_throughput_and_operation_counts() -> None:
    service = PerformanceBenchmarkService(
        InMemoryPerformanceBenchmarkRepository(
            (
                PerformanceBenchmarkRecord("bench-1", "forecast_batch", records_processed=100, duration_ms=1000.0, memory_mb=128.0),
                PerformanceBenchmarkRecord("bench-2", "forecast_batch", records_processed=300, duration_ms=1500.0, memory_mb=256.0),
                PerformanceBenchmarkRecord("bench-3", "snapshot_read", records_processed=50, duration_ms=500.0, memory_mb=64.0),
            )
        )
    )

    summary = service.summarize()

    assert summary.benchmark_count == 3
    assert summary.successful_benchmarks == 3
    assert summary.failed_benchmarks == 0
    assert summary.average_duration_ms == 1000.0
    assert summary.average_throughput_per_second == 133.3333
    assert summary.max_memory_mb == 256.0
    assert summary.operation_counts == {"forecast_batch": 2, "snapshot_read": 1}
    assert summary.health_status == PerformanceHealthStatus.HEALTHY
    assert summary.advisory_only is True
    assert summary.read_only is True


def test_phase_6h_detects_watch_for_high_memory_usage() -> None:
    service = PerformanceBenchmarkService(
        InMemoryPerformanceBenchmarkRepository(
            (PerformanceBenchmarkRecord("bench-1", "forecast_batch", records_processed=100, duration_ms=1000.0, memory_mb=2048.0),)
        )
    )

    summary = service.summarize()

    assert summary.health_status == PerformanceHealthStatus.WATCH
    assert summary.max_memory_mb == 2048.0
    assert summary.warnings == ("High memory usage was observed in benchmark records.",)


def test_phase_6h_detects_degraded_for_failed_benchmark() -> None:
    service = PerformanceBenchmarkService(
        InMemoryPerformanceBenchmarkRepository(
            (PerformanceBenchmarkRecord("bench-1", "forecast_batch", records_processed=0, duration_ms=10.0, success=False),)
        )
    )

    summary = service.summarize()

    assert summary.health_status == PerformanceHealthStatus.DEGRADED
    assert summary.failed_benchmarks == 1
    assert summary.warnings == ("1 performance benchmark failure(s) were observed.",)


def test_phase_6h_rejects_invalid_benchmark_records() -> None:
    with pytest.raises(ValueError, match="records_processed must be"):
        PerformanceBenchmarkRecord("bench-1", "forecast_batch", records_processed=-1, duration_ms=1.0)

    with pytest.raises(ValueError, match="duration_ms must be"):
        PerformanceBenchmarkRecord("bench-1", "forecast_batch", records_processed=1, duration_ms=-1.0)

    record = PerformanceBenchmarkRecord("bench-1", "forecast_batch", records_processed=1, duration_ms=1.0)
    with pytest.raises(ValueError, match="performance benchmarks must remain advisory-only"):
        replace(record, advisory_only=False)


def test_phase_6h_rejects_duplicate_benchmark_records() -> None:
    repository = InMemoryPerformanceBenchmarkRepository()
    repository.record(PerformanceBenchmarkRecord("bench-1", "forecast_batch", records_processed=1, duration_ms=1.0))

    with pytest.raises(ValueError, match="benchmark already recorded"):
        repository.record(PerformanceBenchmarkRecord("bench-1", "forecast_batch", records_processed=1, duration_ms=1.0))


def test_phase_6h_performance_api_returns_read_only_summary() -> None:
    response = client.get("/v1/performance/summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["api_version"] == "v1"
    assert payload["resource"] == "performance_summary"
    assert payload["advisory_only"] is True
    assert payload["read_only"] is True
    assert payload["inventory_source_of_truth_preserved"] is True
    assert payload["data"]["health_status"] == "HEALTHY"
    assert payload["data"]["benchmark_count"] == 0


def test_phase_6h_metadata_lists_performance_endpoint() -> None:
    response = client.get("/v1")

    assert response.status_code == 200
    assert "/v1/performance/summary" in response.json()["data"]["stable_resources"]
