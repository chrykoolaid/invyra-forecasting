from __future__ import annotations

import os
from datetime import datetime, timezone

try:
    from fastapi import APIRouter, HTTPException
except ImportError as exc:  # pragma: no cover
    raise RuntimeError(
        "FastAPI is optional. Install API dependencies with: pip install -e '.[api]'"
    ) from exc

from invyra_forecasting.api.production_contracts import production_envelope
from invyra_forecasting.certified_statistics_persistence import JsonlCertifiedStatisticsRepository
from invyra_forecasting.enterprise_forecast_health import EnterpriseForecastHealthPolicy
from invyra_forecasting.enterprise_intelligence_summary import (
    EnterpriseForecastIntelligenceSummaryService,
    EnterpriseModelIntelligenceInput,
)
from invyra_forecasting.enterprise_portfolio_risk import EnterprisePortfolioRiskPolicy
from invyra_forecasting.model_confidence_governance import ModelConfidenceGovernancePolicy
from invyra_forecasting.model_performance_registry import JsonlModelPerformanceRegistry
from invyra_forecasting.model_performance_statistics import ModelPerformanceStatistics

router = APIRouter(tags=["enterprise-intelligence"])


def _empty_statistics(entry) -> ModelPerformanceStatistics:
    return ModelPerformanceStatistics(
        registry_id=entry.registry_id,
        model_name=entry.model_name,
        model_version=entry.model_version,
        forecast_horizon_days=None,
        eligible_evaluation_count=0,
        mae=None,
        rmse=None,
        mape=None,
        bias=None,
        average_accuracy_score=None,
        average_calibration_gap=None,
    )


def _summary_inputs() -> tuple[EnterpriseModelIntelligenceInput, ...]:
    registry = JsonlModelPerformanceRegistry(
        os.getenv("INVYRA_MODEL_PERFORMANCE_REGISTRY_PATH", "data/model-performance-registry.jsonl")
    )
    certified = JsonlCertifiedStatisticsRepository(
        os.getenv("INVYRA_CERTIFIED_STATISTICS_PATH", "data/certified-model-statistics.jsonl")
    )
    records_by_registry: dict[str, list] = {}
    for record in certified.latest_by_identity():
        records_by_registry.setdefault(record.statistics.registry_id, []).append(record)

    confidence_policy = ModelConfidenceGovernancePolicy()
    inputs: list[EnterpriseModelIntelligenceInput] = []
    for entry in registry.all():
        records = records_by_registry.get(entry.registry_id, ())
        if not records:
            statistics = _empty_statistics(entry)
            inputs.append(EnterpriseModelIntelligenceInput(
                registry_entry=entry,
                statistics=statistics,
                confidence=confidence_policy.assess(entry, statistics),
                evidence_refs=(),
            ))
            continue
        for record in records:
            statistics = record.statistics
            inputs.append(EnterpriseModelIntelligenceInput(
                registry_entry=entry,
                statistics=statistics,
                confidence=confidence_policy.assess(entry, statistics),
                evidence_refs=record.evidence_refs,
            ))
    return tuple(inputs)


def _summary(as_of_utc: str | None):
    resolved_as_of = as_of_utc or datetime.now(timezone.utc).isoformat()
    return EnterpriseForecastIntelligenceSummaryService().summarize(
        _summary_inputs(), as_of_utc=resolved_as_of
    )


@router.get("/v1/intelligence/enterprise/summary")
def get_enterprise_intelligence_summary(as_of_utc: str | None = None) -> dict:
    try:
        summary = _summary(as_of_utc)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return production_envelope(
        "enterprise_forecast_intelligence_summary",
        summary.to_dict(),
        certified_statistics_available=summary.total_eligible_evaluation_count > 0,
    )


@router.get("/v1/intelligence/enterprise/health")
def get_enterprise_forecast_health(as_of_utc: str | None = None) -> dict:
    try:
        health = EnterpriseForecastHealthPolicy().classify(_summary(as_of_utc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return production_envelope("enterprise_forecast_health", health.to_dict())


@router.get("/v1/intelligence/enterprise/risks")
def get_enterprise_portfolio_risks(as_of_utc: str | None = None) -> dict:
    try:
        health = EnterpriseForecastHealthPolicy().classify(_summary(as_of_utc))
        assessment = EnterprisePortfolioRiskPolicy().assess(health)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return production_envelope("enterprise_portfolio_risk_signals", assessment.to_dict())
