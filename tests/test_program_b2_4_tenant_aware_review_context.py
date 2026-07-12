from __future__ import annotations

from contextlib import contextmanager

from invyra_forecasting.api import tenant_context
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


def _context(review_id: str, forecast_id: str) -> ForecastReviewContext:
    return ForecastReviewContext(
        review_id=review_id,
        forecast_id=forecast_id,
        evidence_refs=("evidence-1",),
        metadata={"source": "decision-review"},
    )


def test_review_context_is_isolated_by_namespace():
    repository = InMemoryForecastReviewContextRepository()

    with _tenant("alpha"):
        repository.save(_context("shared-review", "forecast-alpha"))

    with _tenant("bravo"):
        repository.save(_context("shared-review", "forecast-bravo"))

    with _tenant("alpha"):
        assert repository.get("shared-review").forecast_id == "forecast-alpha"

    with _tenant("bravo"):
        assert repository.get("shared-review").forecast_id == "forecast-bravo"


def test_default_namespace_isolated_from_named_namespace():
    repository = InMemoryForecastReviewContextRepository()

    with _tenant(None):
        repository.save(_context("default-review", "forecast-default"))
        assert repository.exists("default-review")

    with _tenant("alpha"):
        assert repository.get("default-review") is None
        assert repository.all() == ()


def test_duplicate_review_id_rejected_only_within_same_namespace():
    repository = InMemoryForecastReviewContextRepository()

    with _tenant("alpha"):
        repository.save(_context("duplicate", "forecast-1"))
        try:
            repository.save(_context("duplicate", "forecast-2"))
        except ValueError as exc:
            assert str(exc) == "review context already exists: duplicate"
        else:
            raise AssertionError("duplicate review context should be rejected")

    with _tenant("bravo"):
        repository.save(_context("duplicate", "forecast-2"))
        assert repository.get("duplicate").forecast_id == "forecast-2"


def test_review_context_preserves_advisory_read_only_guardrails():
    context = _context("review-1", "forecast-1")

    assert context.advisory_only is True
    assert context.read_only is True
    assert context.inventory_source_of_truth_preserved is True
