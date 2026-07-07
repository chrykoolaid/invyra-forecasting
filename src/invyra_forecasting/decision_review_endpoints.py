from __future__ import annotations

from fastapi import APIRouter, FastAPI, HTTPException

from invyra_forecasting.decision_review_api import DecisionReviewApiResponseBuilder
from invyra_forecasting.decision_review_dashboard import DecisionReviewDashboardProjectionBuilder
from invyra_forecasting.decision_review_export import DecisionReviewExportProjectionBuilder
from invyra_forecasting.decision_review_export_bundle import DecisionReviewExportBundleBuilder
from invyra_forecasting.decision_review_store import InMemoryDecisionReviewQueueStore


class DecisionReviewEndpointProjectionService:
    """Read-only endpoint adapter for existing Phase 8 decision review projections."""

    def __init__(
        self,
        *,
        queue_store: InMemoryDecisionReviewQueueStore | None = None,
        dashboard_builder: DecisionReviewDashboardProjectionBuilder | None = None,
        response_builder: DecisionReviewApiResponseBuilder | None = None,
        export_builder: DecisionReviewExportProjectionBuilder | None = None,
        bundle_builder: DecisionReviewExportBundleBuilder | None = None,
    ) -> None:
        self._queue_store = queue_store or InMemoryDecisionReviewQueueStore()
        self._dashboard_builder = dashboard_builder or DecisionReviewDashboardProjectionBuilder()
        self._response_builder = response_builder or DecisionReviewApiResponseBuilder()
        self._export_builder = export_builder or DecisionReviewExportProjectionBuilder()
        self._bundle_builder = bundle_builder or DecisionReviewExportBundleBuilder()

    def dashboard_payload(self) -> dict[str, object]:
        dashboard = self._dashboard_builder.build(self._queue_store.snapshot())
        return self._response_builder.build(dashboard).to_dict()

    def export_payload(self, *, export_format: str = "json") -> dict[str, object]:
        dashboard = self._dashboard_builder.build(self._queue_store.snapshot())
        response = self._response_builder.build(dashboard)
        export = self._export_builder.build(response, export_format=export_format)
        return self._bundle_builder.build(export).to_dict()


def create_decision_review_router(
    *,
    projection_service: DecisionReviewEndpointProjectionService | None = None,
) -> APIRouter:
    """Create read-only Phase 9A endpoints for existing decision review projections."""

    service = projection_service or DecisionReviewEndpointProjectionService()
    router = APIRouter(prefix="/forecast/decision-review", tags=["forecast-decision-review"])

    @router.get("/dashboard")
    def get_decision_review_dashboard() -> dict[str, object]:
        return service.dashboard_payload()

    @router.get("/export")
    def get_decision_review_export(export_format: str = "json") -> dict[str, object]:
        try:
            return service.export_payload(export_format=export_format)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return router


def create_decision_review_app(
    *,
    projection_service: DecisionReviewEndpointProjectionService | None = None,
) -> FastAPI:
    """Create a minimal read-only FastAPI app for Phase 9A endpoint testing/integration."""

    app = FastAPI(title="Invyra Forecast Decision Review API", version="9A.1")
    app.include_router(create_decision_review_router(projection_service=projection_service))
    return app


app = create_decision_review_app()
