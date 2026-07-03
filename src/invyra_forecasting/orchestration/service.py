from __future__ import annotations

from invyra_forecasting.intelligence import ForecastIntelligencePipeline, ForecastIntelligenceRequest
from invyra_forecasting.models import ForecastModelService
from invyra_forecasting.orchestration.contracts import AdvisoryForecastRequest, AdvisoryForecastResponse
from invyra_forecasting.signals.registry import InMemoryForecastSignalRegistry


class AdvisoryForecastOrchestrator:
    """Coordinates signal intelligence and model execution for advisory forecasts."""

    def __init__(
        self,
        registry: InMemoryForecastSignalRegistry,
        *,
        intelligence_pipeline: ForecastIntelligencePipeline | None = None,
        model_service: ForecastModelService | None = None,
    ) -> None:
        self._registry = registry
        self._intelligence_pipeline = intelligence_pipeline or ForecastIntelligencePipeline(registry)
        self._model_service = model_service or ForecastModelService()

    def forecast(self, request: AdvisoryForecastRequest) -> AdvisoryForecastResponse:
        intelligence = self._intelligence_pipeline.build(
            ForecastIntelligenceRequest(
                item_id=request.item_id,
                location_id=request.location_id,
                environment=request.environment,
                analysis_window_days=request.analysis_window_days,
            )
        )
        model_output = self._model_service.forecast(intelligence, forecast_days=request.forecast_days)

        return AdvisoryForecastResponse(
            item_id=model_output.item_id,
            location_id=model_output.location_id,
            environment=model_output.environment,
            analysis_window_days=request.analysis_window_days,
            forecast_days=model_output.forecast_days,
            forecast_quantity=model_output.forecast_quantity,
            projected_days_of_cover=model_output.projected_days_of_cover,
            stockout_risk=model_output.stockout_risk,
            confidence=model_output.confidence,
            explanation=model_output.explanation,
            evidence_refs=model_output.evidence_refs,
            intelligence_summary={
                "signal_count": intelligence.features.signal_count,
                "weighted_signal_count": intelligence.features.weighted_signal_count,
                "quality_assessment_count": len(intelligence.quality_assessments),
                "evidence_link_count": len(intelligence.evidence_links),
                "pipeline_phase": intelligence.processing_metadata.get("pipeline_phase"),
            },
            model_metadata={
                "model_name": model_output.model_name,
                "model_version": model_output.model_version,
                "advisory_only": model_output.advisory_only,
                "inventory_source_of_truth_preserved": model_output.inventory_source_of_truth_preserved,
            },
            advisory_only=True,
            inventory_source_of_truth_preserved=True,
        )

    def registered_signal_count(self) -> int:
        return self._registry.count()
