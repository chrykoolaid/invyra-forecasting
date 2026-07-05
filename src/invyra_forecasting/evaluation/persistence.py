from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable

from invyra_forecasting.evaluation.metrics import ForecastEvaluationResult


@dataclass(frozen=True)
class ForecastEvaluationRecord:
    evaluation_id: str
    result: ForecastEvaluationResult
    persisted_at_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    snapshot_id: str | None = None
    evidence_refs: tuple[str, ...] = ()
    audit_refs: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    advisory_only: bool = True
    read_only: bool = True
    inventory_source_of_truth_preserved: bool = True

    def __post_init__(self) -> None:
        if not self.evaluation_id:
            raise ValueError("evaluation_id is required")
        if not self.advisory_only:
            raise ValueError("evaluation record must be advisory-only")
        if not self.read_only:
            raise ValueError("evaluation record must be read-only")
        if not self.inventory_source_of_truth_preserved:
            raise ValueError("inventory source of truth must be preserved")

    @property
    def forecast_id(self) -> str:
        return self.result.forecast_id

    @property
    def model_name(self) -> str:
        return self.result.model_name

    @property
    def model_version(self) -> str:
        return self.result.model_version

    @property
    def item_id(self) -> str:
        return self.result.item_id

    @property
    def location_id(self) -> str:
        return self.result.location_id

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["result"] = self.result.to_dict()
        payload["evidence_refs"] = list(self.evidence_refs)
        payload["audit_refs"] = list(self.audit_refs)
        return payload


@dataclass(frozen=True)
class EvaluationQuery:
    forecast_id: str | None = None
    item_id: str | None = None
    location_id: str | None = None
    model_name: str | None = None
    model_version: str | None = None
    snapshot_id: str | None = None


class InMemoryForecastEvaluationRepository:
    def __init__(self, records: Iterable[ForecastEvaluationRecord] = ()) -> None:
        self._records: dict[str, ForecastEvaluationRecord] = {}
        for record in records:
            self.save(record)

    def save(self, record: ForecastEvaluationRecord) -> ForecastEvaluationRecord:
        if record.evaluation_id in self._records:
            raise ValueError(f"evaluation already persisted: {record.evaluation_id}")
        self._records[record.evaluation_id] = record
        return record

    def get(self, evaluation_id: str) -> ForecastEvaluationRecord | None:
        return self._records.get(evaluation_id)

    def all(self) -> tuple[ForecastEvaluationRecord, ...]:
        return tuple(sorted(self._records.values(), key=lambda record: (record.persisted_at_utc, record.evaluation_id)))

    def query(self, query: EvaluationQuery) -> tuple[ForecastEvaluationRecord, ...]:
        records = self.all()
        if query.forecast_id is not None:
            records = tuple(record for record in records if record.forecast_id == query.forecast_id)
        if query.item_id is not None:
            records = tuple(record for record in records if record.item_id == query.item_id)
        if query.location_id is not None:
            records = tuple(record for record in records if record.location_id == query.location_id)
        if query.model_name is not None:
            records = tuple(record for record in records if record.model_name == query.model_name)
        if query.model_version is not None:
            records = tuple(record for record in records if record.model_version == query.model_version)
        if query.snapshot_id is not None:
            records = tuple(record for record in records if record.snapshot_id == query.snapshot_id)
        return records


class EvaluationPersistenceService:
    def __init__(self, repository: InMemoryForecastEvaluationRepository | None = None) -> None:
        self._repository = repository or InMemoryForecastEvaluationRepository()

    def persist(
        self,
        result: ForecastEvaluationResult,
        *,
        evaluation_id: str | None = None,
        snapshot_id: str | None = None,
        evidence_refs: Iterable[str] = (),
        audit_refs: Iterable[str] = (),
        metadata: dict[str, Any] | None = None,
    ) -> ForecastEvaluationRecord:
        resolved_id = evaluation_id or self._default_evaluation_id(result, snapshot_id=snapshot_id)
        record = ForecastEvaluationRecord(
            evaluation_id=resolved_id,
            result=result,
            snapshot_id=snapshot_id,
            evidence_refs=tuple(evidence_refs),
            audit_refs=tuple(audit_refs),
            metadata=dict(metadata or {}),
        )
        return self._repository.save(record)

    def get(self, evaluation_id: str) -> ForecastEvaluationRecord | None:
        return self._repository.get(evaluation_id)

    def query(self, query: EvaluationQuery) -> tuple[ForecastEvaluationRecord, ...]:
        return self._repository.query(query)

    def timeline_for_forecast(self, forecast_id: str) -> tuple[ForecastEvaluationRecord, ...]:
        return self.query(EvaluationQuery(forecast_id=forecast_id))

    def summarize(self, query: EvaluationQuery | None = None) -> dict[str, Any]:
        records = self._repository.all() if query is None else self.query(query)
        if not records:
            return {
                "count": 0,
                "mae": None,
                "rmse": None,
                "mape": None,
                "bias": None,
                "average_accuracy_score": None,
                "advisory_only": True,
                "read_only": True,
                "inventory_source_of_truth_preserved": True,
            }
        count = len(records)
        mae = sum(record.result.absolute_error for record in records) / count
        rmse = (sum(record.result.squared_error for record in records) / count) ** 0.5
        ape_values = [record.result.absolute_percentage_error for record in records if record.result.absolute_percentage_error is not None]
        mape = None if not ape_values else sum(ape_values) / len(ape_values)
        bias = sum(record.result.bias for record in records) / count
        accuracy = sum(record.result.accuracy_score for record in records) / count
        return {
            "count": count,
            "mae": round(mae, 4),
            "rmse": round(rmse, 4),
            "mape": None if mape is None else round(mape, 4),
            "bias": round(bias, 4),
            "average_accuracy_score": round(accuracy, 4),
            "advisory_only": True,
            "read_only": True,
            "inventory_source_of_truth_preserved": True,
        }

    def _default_evaluation_id(self, result: ForecastEvaluationResult, *, snapshot_id: str | None) -> str:
        snapshot_part = snapshot_id or "no_snapshot"
        return "::".join((result.forecast_id, result.model_name, result.model_version, snapshot_part))
