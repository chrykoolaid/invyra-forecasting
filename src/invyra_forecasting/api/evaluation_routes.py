from __future__ import annotations

import os

try:
    from fastapi import APIRouter, HTTPException
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("FastAPI is optional. Install API dependencies with: pip install -e '.[api]'") from exc

from invyra_forecasting.api.production_contracts import production_envelope
from invyra_forecasting.evaluation_evidence_persistence import (
    EvaluationEvidenceStage,
    JsonlEvaluationEvidenceRepository,
)
from invyra_forecasting.evaluation_read_models import (
    EvaluationEvidenceQuery,
    EvaluationEvidenceReadService,
)

router = APIRouter(tags=["evaluations"])


def _read_service() -> EvaluationEvidenceReadService:
    repository = JsonlEvaluationEvidenceRepository(
        os.getenv("INVYRA_EVALUATION_EVIDENCE_PATH", "data/evaluation-evidence.jsonl")
    )
    return EvaluationEvidenceReadService(repository)


@router.get("/v1/evaluations")
def list_evaluations(
    evaluation_id: str | None = None,
    history_id: str | None = None,
    forecast_id: str | None = None,
    item_id: str | None = None,
    location_id: str | None = None,
    model_name: str | None = None,
    model_version: str | None = None,
    stage: EvaluationEvidenceStage | None = None,
    limit: int = 100,
    offset: int = 0,
) -> dict:
    try:
        result = _read_service().list(
            EvaluationEvidenceQuery(
                evaluation_id=evaluation_id,
                history_id=history_id,
                forecast_id=forecast_id,
                item_id=item_id,
                location_id=location_id,
                model_name=model_name,
                model_version=model_version,
                stage=stage,
            ),
            limit=limit,
            offset=offset,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return production_envelope("evaluation_evidence", result)


@router.get("/v1/evaluations/{evaluation_id}")
def get_evaluation_timeline(evaluation_id: str) -> dict:
    records = _read_service().evaluation_timeline(evaluation_id)
    if not records:
        raise HTTPException(status_code=404, detail=f"Evaluation evidence not found: {evaluation_id}")
    return production_envelope(
        "evaluation_evidence_timeline",
        {
            "evaluation_id": evaluation_id,
            "items": [record.to_dict() for record in records],
            "total": len(records),
        },
    )


@router.get("/v1/evaluations/history/{history_id}")
def get_history_evaluation(history_id: str) -> dict:
    records = _read_service().history_evaluation(history_id)
    if not records:
        raise HTTPException(status_code=404, detail=f"Evaluation evidence not found for history: {history_id}")
    return production_envelope(
        "history_evaluation_evidence",
        {
            "history_id": history_id,
            "items": [record.to_dict() for record in records],
            "total": len(records),
        },
    )


@router.get("/v1/models/{model_name}/performance")
def get_model_performance_evidence(model_name: str, model_version: str | None = None) -> dict:
    summary = _read_service().model_performance_evidence(
        model_name,
        model_version=model_version,
    )
    return production_envelope("model_performance_evidence", summary)
