from __future__ import annotations

from dataclasses import replace
from datetime import date

from invyra_forecasting.explanation import enrich_explanation_with_intelligence_context
from invyra_forecasting.intelligence import ForecastIntelligencePipeline, ForecastIntelligenceRequest
from invyra_forecasting.intelligence_summary import summarize_forecast_intelligence
from invyra_forecasting.schemas import ForecastInputBundle, ForecastSnapshot
from invyra_forecasting.services.forecasting_service import ForecastingService
from invyra_forecasting.signals import InMemoryForecastSignalRegistry


def run_item_forecast_with_registry_intelligence(
    service: ForecastingService,
    bundle: ForecastInputBundle,
    registry: InMemoryForecastSignalRegistry,
    actor: str = "system",
    anchor_date: date | None = None,
    write_snapshot: bool = False,
    write_audit: bool | None = None,
    analysis_window_days: int = 30,
) -> ForecastSnapshot:
    intelligence = ForecastIntelligencePipeline(registry).build(
        ForecastIntelligenceRequest(
            item_id=bundle.item.item_id,
            location_id=bundle.location.location_id,
            environment=bundle.environment,
            analysis_window_days=analysis_window_days,
        )
    )
    summary = summarize_forecast_intelligence(intelligence)
    intelligence_context = summary.to_dict()
    snapshot = service.run_item_forecast(
        bundle,
        actor=actor,
        anchor_date=anchor_date,
        write_snapshot=write_snapshot,
        write_audit=write_audit,
        intelligence_context=intelligence_context,
    )
    return replace(
        snapshot,
        explanation=enrich_explanation_with_intelligence_context(snapshot.explanation, intelligence_context),
    )
