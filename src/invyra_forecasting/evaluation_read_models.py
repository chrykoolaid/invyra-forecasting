from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from invyra_forecasting.evaluation_evidence_persistence import (
    EvaluationEvidenceRecord,
    EvaluationEvidenceStage,
    InMemoryEvaluationEvidenceRepository,
)


@dataclass(frozen=True)
class EvaluationEvidenceQuery:
    evaluation_id: str | None = None
    history_id: str | None = None
    forecast_id: str | None = None
    item_id: str | None = None
    location_id: str | None = None
    model_name: str | None = None
    model_version: str | None = None
    stage: EvaluationEvidenceStage | None = None


class EvaluationEvidenceReadService:
    """Tenant-scoped read models over immutable E5 evidence records."""

    def __init__(self, repository: InMemoryEvaluationEvidenceRepository) -> None:
        self._repository = repository

    def list(
        self,
        query: EvaluationEvidenceQuery | None = None,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        if limit < 1 or limit > 1000:
            raise ValueError("limit must be between 1 and 1000")
        if offset < 0:
            raise ValueError("offset must not be negative")
        resolved = query or EvaluationEvidenceQuery()
        records = tuple(record for record in self._repository.all() if self._matches(record, resolved))
        items = records[offset : offset + limit]
        return {
            "items": [record.to_dict() for record in items],
            "total": len(records),
            "limit": limit,
            "offset": offset,
            "advisory_only": True,
            "read_only": True,
            "inventory_source_of_truth_preserved": True,
        }

    def evaluation_timeline(self, evaluation_id: str) -> tuple[EvaluationEvidenceRecord, ...]:
        return self._repository.for_evaluation(evaluation_id)

    def history_evaluation(self, history_id: str) -> tuple[EvaluationEvidenceRecord, ...]:
        return tuple(record for record in self._repository.all() if record.history_id == history_id)

    def model_performance_evidence(
        self,
        model_name: str,
        *,
        model_version: str | None = None,
    ) -> dict[str, Any]:
        records = tuple(
            record
            for record in self._repository.all()
            if record.linkage.get("model_name") == model_name
            and (model_version is None or record.linkage.get("model_version") == model_version)
        )
        final_records = tuple(record for record in records if record.stage is EvaluationEvidenceStage.FINAL)
        ranking_eligible = tuple(
            record
            for record in final_records
            if record.censoring_assessment.get("ranking_evidence_eligible") is True
        )
        censoring_counts: dict[str, int] = {}
        for record in records:
            status = str(record.censoring_assessment.get("status", "unknown"))
            censoring_counts[status] = censoring_counts.get(status, 0) + 1
        return {
            "model_name": model_name,
            "model_version": model_version,
            "evidence_record_count": len(records),
            "partial_record_count": len(records) - len(final_records),
            "final_record_count": len(final_records),
            "ranking_eligible_final_count": len(ranking_eligible),
            "censoring_status_counts": censoring_counts,
            "accuracy_metrics_calculated": False,
            "advisory_only": True,
            "read_only": True,
            "inventory_source_of_truth_preserved": True,
        }

    @staticmethod
    def _matches(record: EvaluationEvidenceRecord, query: EvaluationEvidenceQuery) -> bool:
        linkage = record.linkage
        checks = (
            query.evaluation_id is None or record.evaluation_id == query.evaluation_id,
            query.history_id is None or record.history_id == query.history_id,
            query.forecast_id is None or record.forecast_id == query.forecast_id,
            query.item_id is None or linkage.get("item_id") == query.item_id,
            query.location_id is None or linkage.get("location_id") == query.location_id,
            query.model_name is None or linkage.get("model_name") == query.model_name,
            query.model_version is None or linkage.get("model_version") == query.model_version,
            query.stage is None or record.stage is query.stage,
        )
        return all(checks)
