from __future__ import annotations

import asyncio
from contextlib import contextmanager
from dataclasses import dataclass

from invyra_forecasting.api import tenant_context
from invyra_forecasting.api.tenant_namespace import DEFAULT_NAMESPACE, current_namespace
from invyra_forecasting.data.repositories import FileSnapshotRepository
from invyra_forecasting.monitoring import (
    ForecastMonitoringEvent,
    ForecastMonitoringService,
    InMemoryForecastMonitoringRepository,
)
from invyra_forecasting.review_context import (
    ForecastReviewContext,
    InMemoryForecastReviewContextRepository,
)


@contextmanager
def _tenant(tenant_id: str | None):
    token = tenant_context._TENANT_ID.set(tenant_context.normalize_tenant_id(tenant_id))
    try:
        yield
    finally:
        tenant_context._TENANT_ID.reset(token)


@dataclass(frozen=True)
class _Forecast:
    item_id: str


@dataclass(frozen=True)
class _Snapshot:
    snapshot_id: str
    forecast: _Forecast


def _monitoring_event(event_id: str, confidence: float) -> ForecastMonitoringEvent:
    return ForecastMonitoringEvent(
        event_id=event_id,
        event_type="forecast",
        model_id="certification-model",
        confidence=confidence,
        latency_ms=5.0,
    )


def _review_context(review_id: str, forecast_id: str) -> ForecastReviewContext:
    return ForecastReviewContext(
        review_id=review_id,
        forecast_id=forecast_id,
        evidence_refs=("certification-evidence",),
    )


def test_cross_component_isolation_with_shared_identifiers(tmp_path):
    snapshots = FileSnapshotRepository(tmp_path)
    monitoring = ForecastMonitoringService(InMemoryForecastMonitoringRepository())
    reviews = InMemoryForecastReviewContextRepository()

    with _tenant("alpha"):
        snapshots.save(_Snapshot("shared-id", _Forecast("alpha-item")))
        monitoring.record_event(_monitoring_event("shared-id", 0.9))
        reviews.save(_review_context("shared-id", "alpha-forecast"))

    with _tenant("bravo"):
        snapshots.save(_Snapshot("shared-id", _Forecast("bravo-item")))
        monitoring.record_event(_monitoring_event("shared-id", 0.4))
        reviews.save(_review_context("shared-id", "bravo-forecast"))

    with _tenant("alpha"):
        assert snapshots.get("shared-id")["forecast"]["item_id"] == "alpha-item"
        assert monitoring.snapshot().average_confidence == 0.9
        assert reviews.get("shared-id").forecast_id == "alpha-forecast"

    with _tenant("bravo"):
        assert snapshots.get("shared-id")["forecast"]["item_id"] == "bravo-item"
        assert monitoring.snapshot().average_confidence == 0.4
        assert reviews.get("shared-id").forecast_id == "bravo-forecast"


def test_default_namespace_remains_backward_compatible(tmp_path):
    snapshots = FileSnapshotRepository(tmp_path)
    monitoring = ForecastMonitoringService(InMemoryForecastMonitoringRepository())
    reviews = InMemoryForecastReviewContextRepository()

    with _tenant(None):
        assert current_namespace() == DEFAULT_NAMESPACE
        path = snapshots.save(_Snapshot("default-id", _Forecast("default-item")))
        monitoring.record_event(_monitoring_event("default-id", 0.8))
        reviews.save(_review_context("default-id", "default-forecast"))

        assert path == tmp_path / "default-id.json"
        assert monitoring.snapshot().forecast_count == 1
        assert reviews.exists("default-id")

    with _tenant("alpha"):
        assert snapshots.get("default-id") is None
        assert monitoring.snapshot().forecast_count == 0
        assert not reviews.exists("default-id")


def test_request_context_isolation_under_concurrency():
    async def worker(tenant_id: str) -> tuple[str, str]:
        token = tenant_context._TENANT_ID.set(tenant_id)
        try:
            await asyncio.sleep(0)
            return tenant_id, current_namespace()
        finally:
            tenant_context._TENANT_ID.reset(token)

    async def run() -> list[tuple[str, str]]:
        return await asyncio.gather(
            worker("alpha"),
            worker("bravo"),
            worker("charlie"),
            worker("delta"),
        )

    assert asyncio.run(run()) == [
        ("alpha", "alpha"),
        ("bravo", "bravo"),
        ("charlie", "charlie"),
        ("delta", "delta"),
    ]
    assert current_namespace() == DEFAULT_NAMESPACE


def test_guardrails_remain_enforced_across_tenant_components():
    event = _monitoring_event("event-1", 0.7)
    review = _review_context("review-1", "forecast-1")

    assert event.advisory_only is True
    assert event.read_only is True
    assert event.inventory_source_of_truth_preserved is True
    assert review.advisory_only is True
    assert review.read_only is True
    assert review.inventory_source_of_truth_preserved is True
