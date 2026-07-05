from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any, Iterable


class PerformanceHealthStatus(StrEnum):
    HEALTHY = "HEALTHY"
    WATCH = "WATCH"
    DEGRADED = "DEGRADED"


@dataclass(frozen=True)
class PerformanceBenchmarkRecord:
    benchmark_id: str
    operation: str
    records_processed: int
    duration_ms: float
    memory_mb: float | None = None
    success: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)
    advisory_only: bool = True
    read_only: bool = True
    inventory_source_of_truth_preserved: bool = True

    def __post_init__(self) -> None:
        if not self.benchmark_id:
            raise ValueError("benchmark_id is required")
        if not self.operation:
            raise ValueError("operation is required")
        if self.records_processed < 0:
            raise ValueError("records_processed must be greater than or equal to 0")
        if self.duration_ms < 0:
            raise ValueError("duration_ms must be greater than or equal to 0")
        if self.memory_mb is not None and self.memory_mb < 0:
            raise ValueError("memory_mb must be greater than or equal to 0")
        if not self.advisory_only:
            raise ValueError("performance benchmarks must remain advisory-only")
        if not self.read_only:
            raise ValueError("performance benchmarks must remain read-only")
        if not self.inventory_source_of_truth_preserved:
            raise ValueError("inventory source of truth must be preserved")

    @property
    def throughput_per_second(self) -> float | None:
        if self.duration_ms <= 0:
            return None
        return round(self.records_processed / (self.duration_ms / 1000.0), 4)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["throughput_per_second"] = self.throughput_per_second
        return payload


@dataclass(frozen=True)
class PerformanceSummary:
    benchmark_count: int
    successful_benchmarks: int
    failed_benchmarks: int
    average_duration_ms: float | None
    average_throughput_per_second: float | None
    max_memory_mb: float | None
    operation_counts: dict[str, int]
    health_status: PerformanceHealthStatus
    warnings: tuple[str, ...] = ()
    advisory_only: bool = True
    read_only: bool = True
    inventory_source_of_truth_preserved: bool = True

    def __post_init__(self) -> None:
        if not self.advisory_only:
            raise ValueError("performance summaries must remain advisory-only")
        if not self.read_only:
            raise ValueError("performance summaries must remain read-only")
        if not self.inventory_source_of_truth_preserved:
            raise ValueError("inventory source of truth must be preserved")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["health_status"] = self.health_status.value
        payload["warnings"] = list(self.warnings)
        return payload


class InMemoryPerformanceBenchmarkRepository:
    def __init__(self, records: Iterable[PerformanceBenchmarkRecord] = ()) -> None:
        self._records: dict[str, PerformanceBenchmarkRecord] = {}
        for record in records:
            self.record(record)

    def record(self, record: PerformanceBenchmarkRecord) -> PerformanceBenchmarkRecord:
        if record.benchmark_id in self._records:
            raise ValueError(f"benchmark already recorded: {record.benchmark_id}")
        self._records[record.benchmark_id] = record
        return record

    def all(self) -> tuple[PerformanceBenchmarkRecord, ...]:
        return tuple(self._records.values())


class PerformanceBenchmarkService:
    def __init__(self, repository: InMemoryPerformanceBenchmarkRepository | None = None) -> None:
        self._repository = repository or InMemoryPerformanceBenchmarkRepository()

    def record(self, record: PerformanceBenchmarkRecord) -> PerformanceBenchmarkRecord:
        return self._repository.record(record)

    def summarize(self) -> PerformanceSummary:
        records = self._repository.all()
        benchmark_count = len(records)
        successful = len(tuple(record for record in records if record.success))
        failed = benchmark_count - successful
        durations = [record.duration_ms for record in records]
        throughputs = [record.throughput_per_second for record in records if record.throughput_per_second is not None]
        memory_values = [record.memory_mb for record in records if record.memory_mb is not None]
        operation_counts: dict[str, int] = {}
        for record in records:
            operation_counts[record.operation] = operation_counts.get(record.operation, 0) + 1
        warnings: list[str] = []
        if failed > 0:
            warnings.append(f"{failed} performance benchmark failure(s) were observed.")
        if memory_values and max(memory_values) >= 1024:
            warnings.append("High memory usage was observed in benchmark records.")
        return PerformanceSummary(
            benchmark_count=benchmark_count,
            successful_benchmarks=successful,
            failed_benchmarks=failed,
            average_duration_ms=self._average(durations),
            average_throughput_per_second=self._average(throughputs),
            max_memory_mb=None if not memory_values else round(max(memory_values), 4),
            operation_counts=operation_counts,
            health_status=self._health_status(failed=failed, memory_values=memory_values),
            warnings=tuple(warnings),
        )

    def _health_status(self, *, failed: int, memory_values: list[float]) -> PerformanceHealthStatus:
        if failed > 0:
            return PerformanceHealthStatus.DEGRADED
        if memory_values and max(memory_values) >= 1024:
            return PerformanceHealthStatus.WATCH
        return PerformanceHealthStatus.HEALTHY

    def _average(self, values: list[float]) -> float | None:
        if not values:
            return None
        return round(sum(values) / len(values), 4)
