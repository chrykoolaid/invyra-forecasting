from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Iterable
from uuid import uuid4

from invyra_forecasting.actual_outcome import ActualOutcomeEvidence
from invyra_forecasting.api.tenant_namespace import current_namespace
from invyra_forecasting.evaluation_linkage import ForecastEvaluationLink
from invyra_forecasting.evaluation_window import EvaluationWindowAssessment
from invyra_forecasting.stockout_censoring import StockoutCensoringAssessment


class EvaluationEvidenceStage(str, Enum):
    PARTIAL = "partial"
    FINAL = "final"


@dataclass(frozen=True)
class EvaluationEvidenceRecord:
    record_id: str
    evaluation_id: str
    history_id: str
    forecast_id: str
    outcome_evidence_id: str
    stage: EvaluationEvidenceStage
    linkage: dict[str, Any]
    window_assessment: dict[str, Any]
    actual_outcome: dict[str, Any]
    censoring_assessment: dict[str, Any]
    namespace: str
    persisted_at_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    advisory_only: bool = True
    read_only: bool = True
    inventory_source_of_truth_preserved: bool = True

    def __post_init__(self) -> None:
        for name, value in {
            "record_id": self.record_id,
            "evaluation_id": self.evaluation_id,
            "history_id": self.history_id,
            "forecast_id": self.forecast_id,
            "outcome_evidence_id": self.outcome_evidence_id,
            "namespace": self.namespace,
        }.items():
            if not value:
                raise ValueError(f"{name} is required")
        if not self.advisory_only or not self.read_only:
            raise ValueError("evaluation evidence records must remain advisory-only and read-only")
        if not self.inventory_source_of_truth_preserved:
            raise ValueError("inventory source of truth must be preserved")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["stage"] = self.stage.value
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "EvaluationEvidenceRecord":
        return cls(**{**payload, "stage": EvaluationEvidenceStage(payload["stage"])})


class InMemoryEvaluationEvidenceRepository:
    def __init__(self, records: Iterable[EvaluationEvidenceRecord] = ()) -> None:
        self._records_by_namespace: dict[str, dict[str, EvaluationEvidenceRecord]] = {}
        for record in records:
            self._append_loaded(record)

    def _records(self) -> dict[str, EvaluationEvidenceRecord]:
        return self._records_by_namespace.setdefault(current_namespace(), {})

    def _append_loaded(self, record: EvaluationEvidenceRecord) -> None:
        records = self._records_by_namespace.setdefault(record.namespace, {})
        if record.record_id in records:
            raise ValueError(f"evaluation evidence record already exists: {record.record_id}")
        records[record.record_id] = record

    def append(self, record: EvaluationEvidenceRecord) -> EvaluationEvidenceRecord:
        if record.namespace != current_namespace():
            raise ValueError("evaluation evidence namespace must match the active tenant namespace")
        records = self._records()
        if record.record_id in records:
            raise ValueError(f"evaluation evidence record already exists: {record.record_id}")
        if record.stage is EvaluationEvidenceStage.FINAL and any(
            existing.evaluation_id == record.evaluation_id
            and existing.stage is EvaluationEvidenceStage.FINAL
            for existing in records.values()
        ):
            raise ValueError(f"final evaluation evidence already persisted: {record.evaluation_id}")
        records[record.record_id] = record
        return record

    def all(self) -> tuple[EvaluationEvidenceRecord, ...]:
        return tuple(
            sorted(
                self._records().values(),
                key=lambda record: (record.persisted_at_utc, record.record_id),
            )
        )

    def for_evaluation(self, evaluation_id: str) -> tuple[EvaluationEvidenceRecord, ...]:
        return tuple(record for record in self.all() if record.evaluation_id == evaluation_id)


class JsonlEvaluationEvidenceRepository(InMemoryEvaluationEvidenceRepository):
    """Append-only JSONL persistence with tenant-safe reconstruction."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        records: list[EvaluationEvidenceRecord] = []
        if self._path.exists():
            for line in self._path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    records.append(EvaluationEvidenceRecord.from_dict(json.loads(line)))
        super().__init__(records)

    def append(self, record: EvaluationEvidenceRecord) -> EvaluationEvidenceRecord:
        saved = super().append(record)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(saved.to_dict(), sort_keys=True) + "\n")
        return saved


class EvaluationEvidencePersistenceService:
    def __init__(self, repository: InMemoryEvaluationEvidenceRepository | None = None) -> None:
        self._repository = repository or InMemoryEvaluationEvidenceRepository()

    def persist(
        self,
        link: ForecastEvaluationLink,
        window: EvaluationWindowAssessment,
        outcome: ActualOutcomeEvidence,
        censoring: StockoutCensoringAssessment,
        *,
        stage: EvaluationEvidenceStage,
        record_id: str | None = None,
    ) -> EvaluationEvidenceRecord:
        self._validate_identity(link, window, outcome, censoring)
        if stage is EvaluationEvidenceStage.FINAL:
            if not window.final_evaluation_eligible:
                raise ValueError("final evidence requires final evaluation eligibility")
            if not censoring.ranking_evidence_eligible:
                raise ValueError("final evidence requires uncensored complete outcome evidence")
        record = EvaluationEvidenceRecord(
            record_id=record_id or str(uuid4()),
            evaluation_id=link.evaluation_id,
            history_id=link.history_id,
            forecast_id=link.forecast_id,
            outcome_evidence_id=outcome.outcome_evidence_id,
            stage=stage,
            linkage=link.to_dict(),
            window_assessment=window.to_dict(),
            actual_outcome=outcome.to_dict(),
            censoring_assessment=censoring.to_dict(),
            namespace=current_namespace(),
        )
        return self._repository.append(record)

    def for_evaluation(self, evaluation_id: str) -> tuple[EvaluationEvidenceRecord, ...]:
        return self._repository.for_evaluation(evaluation_id)

    @staticmethod
    def _validate_identity(
        link: ForecastEvaluationLink,
        window: EvaluationWindowAssessment,
        outcome: ActualOutcomeEvidence,
        censoring: StockoutCensoringAssessment,
    ) -> None:
        if (link.evaluation_id, link.history_id, link.forecast_id) != (
            window.evaluation_id,
            window.history_id,
            window.forecast_id,
        ):
            raise ValueError("link and evaluation window identities must match")
        if (link.forecast_id, link.item_id, link.location_id) != (
            outcome.forecast_id,
            outcome.item_id,
            outcome.location_id,
        ):
            raise ValueError("link and actual outcome identities must match")
        if (outcome.outcome_evidence_id, outcome.forecast_id, outcome.item_id, outcome.location_id) != (
            censoring.outcome_evidence_id,
            censoring.forecast_id,
            censoring.item_id,
            censoring.location_id,
        ):
            raise ValueError("actual outcome and censoring identities must match")
        objects = (link, window, outcome, censoring)
        if any(not obj.advisory_only or not obj.read_only for obj in objects):
            raise ValueError("persisted evidence must remain advisory-only and read-only")
        if any(not obj.inventory_source_of_truth_preserved for obj in objects):
            raise ValueError("inventory source of truth must be preserved")
