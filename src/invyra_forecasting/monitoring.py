from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any, Iterable


class MonitoringHealthStatus(StrEnum):
    HEALTHY = "HEALTHY"
    WATCH = "WATCH"
    DEGRADED = "DEGRADED"


@dataclass(frozen=True)
class ForecastMonitoringEvent:
    event_id: str
    event_type: str
    model_id: str | None = None
    model_name: str | None = None
    model_version: str | None = None
    confidence: float | None = None
    latency_ms: float | None = None
    drift_severity: str | None = None
    success: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)
    advisory_only: bool = True
    read_only: bool = True
    inventory_source_of_truth_preserved: bool = True

    def __post_init__(self) -> None:
        if not self.event_id:
            raise ValueError("event_id is required")
        if not self.event_type:
            raise ValueError("event_type is required")
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        if self.latency_ms is not None and self.latency_ms < 0:
            raise ValueError("latency_ms must be greater than or equal to 0")
        if not self.advisory_only:
            raise ValueError("monitoring events must remain advisory-only")
        if not self.read_only:
            raise ValueError("monitoring events must remain read-only")
        if not self.inventory_source_of_truth_preserved:
            raise ValueError("inventory source of truth must be preserved")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ForecastMonitoringSnapshot:
    forecast_count: int
    successful_forecasts: int
    failed_forecasts: int
    average_latency_ms: float | None
    average_confidence: float | None
    confidence_distribution: dict[str, int]
    model_usage: dict[str, int]
    drift_counts: dict[str, int]
    health_status: MonitoringHealthStatus
    warnings: tuple[str, ...] = ()
    advisory_only: bool = True
    read_only: bool = True
    inventory_source_of_truth_preserved: bool = True

    def __post_init__(self) -> None:
        if not self.advisory_only:
            raise ValueError("monitoring snapshots must remain advisory-only")
        if not self.read_only:
            raise ValueError("monitoring snapshots must remain read-only")
        if not self.inventory_source_of_truth_preserved:
            raise ValueError("inventory source of truth must be preserved")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["health_status"] = self.health_status.value
        payload["warnings"] = list(self.warnings)
        return payload


class InMemoryForecastMonitoringRepository:
    def __init__(self, events: Iterable[ForecastMonitoringEvent] = ()) -> None:
        self._events: dict[str, ForecastMonitoringEvent] = {}
        for event in events:
            self.record(event)

    def record(self, event: ForecastMonitoringEvent) -> ForecastMonitoringEvent:
        if event.event_id in self._events:
            raise ValueError(f"monitoring event already recorded: {event.event_id}")
        self._events[event.event_id] = event
        return event

    def all(self) -> tuple[ForecastMonitoringEvent, ...]:
        return tuple(self._events.values())


class ForecastMonitoringService:
    def __init__(self, repository: InMemoryForecastMonitoringRepository | None = None) -> None:
        self._repository = repository or InMemoryForecastMonitoringRepository()

    def record_event(self, event: ForecastMonitoringEvent) -> ForecastMonitoringEvent:
        return self._repository.record(event)

    def snapshot(self) -> ForecastMonitoringSnapshot:
        events = self._repository.all()
        forecast_events = tuple(event for event in events if event.event_type == "forecast")
        forecast_count = len(forecast_events)
        successful = len(tuple(event for event in forecast_events if event.success))
        failed = forecast_count - successful
        latencies = [event.latency_ms for event in forecast_events if event.latency_ms is not None]
        confidences = [event.confidence for event in forecast_events if event.confidence is not None]
        warnings: list[str] = []
        drift_counts = self._drift_counts(events)
        if failed > 0:
            warnings.append(f"{failed} forecast failure(s) were observed.")
        if drift_counts.get("CRITICAL", 0) > 0:
            warnings.append("Critical drift report(s) were observed.")
        health = self._health_status(failed=failed, drift_counts=drift_counts)
        return ForecastMonitoringSnapshot(
            forecast_count=forecast_count,
            successful_forecasts=successful,
            failed_forecasts=failed,
            average_latency_ms=self._average(latencies),
            average_confidence=self._average(confidences),
            confidence_distribution=self._confidence_distribution(confidences),
            model_usage=self._model_usage(forecast_events),
            drift_counts=drift_counts,
            health_status=health,
            warnings=tuple(warnings),
        )

    def _health_status(self, *, failed: int, drift_counts: dict[str, int]) -> MonitoringHealthStatus:
        if failed > 0 or drift_counts.get("CRITICAL", 0) > 0:
            return MonitoringHealthStatus.DEGRADED
        if drift_counts.get("WARNING", 0) > 0 or drift_counts.get("WATCH", 0) > 0:
            return MonitoringHealthStatus.WATCH
        return MonitoringHealthStatus.HEALTHY

    def _confidence_distribution(self, confidences: list[float]) -> dict[str, int]:
        distribution = {"low": 0, "medium": 0, "high": 0}
        for confidence in confidences:
            if confidence < 0.5:
                distribution["low"] += 1
            elif confidence < 0.8:
                distribution["medium"] += 1
            else:
                distribution["high"] += 1
        return distribution

    def _model_usage(self, events: tuple[ForecastMonitoringEvent, ...]) -> dict[str, int]:
        usage: dict[str, int] = {}
        for event in events:
            key = event.model_id or event.model_name or "UNKNOWN"
            usage[key] = usage.get(key, 0) + 1
        return usage

    def _drift_counts(self, events: tuple[ForecastMonitoringEvent, ...]) -> dict[str, int]:
        counts: dict[str, int] = {"NONE": 0, "WATCH": 0, "WARNING": 0, "CRITICAL": 0}
        for event in events:
            if event.drift_severity:
                counts[event.drift_severity] = counts.get(event.drift_severity, 0) + 1
        return counts

    def _average(self, values: list[float]) -> float | None:
        if not values:
            return None
        return round(sum(values) / len(values), 4)
