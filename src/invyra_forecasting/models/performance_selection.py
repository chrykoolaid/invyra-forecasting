from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Iterable, Protocol


class RegisteredModelForSelection(Protocol):
    model_id: str
    model_name: str
    supported_forecast_types: tuple[str, ...]
    supported_horizons_days: tuple[int, ...]


@dataclass(frozen=True)
class ModelPerformanceRecord:
    """Historical advisory performance evidence for a registered model.

    These records are read by model selection. They do not mutate inventory,
    create stock movements, create purchase orders, approve purchase orders, or
    override ledger truth.
    """

    model_id: str
    accuracy: float = 0.0
    calibration: float = 0.0
    stability: float = 0.0
    evaluation_count: int = 0
    average_error: float | None = None
    last_evaluated_at: str | None = None
    supported_contexts: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["supported_contexts"] = list(self.supported_contexts)
        return payload


class ModelPerformanceRepository:
    """In-memory repository for historical model performance evidence."""

    def __init__(self, records: Iterable[ModelPerformanceRecord] = ()) -> None:
        self._records = {record.model_id: record for record in records}

    def get(self, model_id: str) -> ModelPerformanceRecord | None:
        return self._records.get(model_id)

    def all(self) -> tuple[ModelPerformanceRecord, ...]:
        return tuple(self._records.values())


@dataclass(frozen=True)
class ModelSelectionContext:
    """Context used to rank eligible models without touching operational data."""

    forecast_type: str
    forecast_days: int
    average_daily_demand: float | None = None
    latest_on_hand: float | None = None
    confidence: float | None = None
    evidence_count: int = 0
    feature_count: int = 0

    @property
    def context_keys(self) -> tuple[str, ...]:
        keys = [self.forecast_type, f"horizon:{self.forecast_days}"]
        if self.evidence_count == 0:
            keys.append("sparse_evidence")
        if self.feature_count > 0:
            keys.append("feature_backed")
        return tuple(keys)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ModelPerformanceScore:
    """Explainable score assigned to one eligible model candidate."""

    model_id: str
    score: float
    components: dict[str, float]
    rationale: tuple[str, ...]
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "model_id": self.model_id,
            "score": self.score,
            "components": dict(self.components),
            "rationale": list(self.rationale),
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class ModelSelectionAuditRecord:
    """Audit-safe record of a model selection decision."""

    selected_model_id: str
    candidate_scores: tuple[ModelPerformanceScore, ...]
    context: ModelSelectionContext
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, object]:
        return {
            "selected_model_id": self.selected_model_id,
            "candidate_scores": [score.to_dict() for score in self.candidate_scores],
            "context": self.context.to_dict(),
            "created_at": self.created_at,
            "advisory_only": True,
            "inventory_source_of_truth_preserved": True,
        }


class PerformanceAwareModelSelector:
    """Ranks eligible models using historical performance and request context."""

    def __init__(self, repository: ModelPerformanceRepository | None = None) -> None:
        self._repository = repository or ModelPerformanceRepository()

    def score_model(self, model: RegisteredModelForSelection, context: ModelSelectionContext) -> ModelPerformanceScore:
        record = self._repository.get(model.model_id)
        warnings: list[str] = []
        rationale: list[str] = []

        if record is None:
            components = {
                "accuracy": 0.5,
                "calibration": 0.5,
                "stability": 0.5,
                "evaluation_depth": 0.0,
                "context_fit": self._context_fit(model, None, context),
            }
            warnings.append("No historical performance record exists for this model; neutral defaults were used.")
        else:
            components = {
                "accuracy": self._clamp(record.accuracy),
                "calibration": self._clamp(record.calibration),
                "stability": self._clamp(record.stability),
                "evaluation_depth": self._evaluation_depth(record.evaluation_count),
                "context_fit": self._context_fit(model, record, context),
            }
            rationale.append(
                f"Historical performance used {record.evaluation_count} evaluation(s) for {model.model_name}."
            )
            if record.average_error is not None:
                rationale.append(f"Average recorded error is {record.average_error:.4f}.")

        score = round(
            components["accuracy"] * 0.35
            + components["calibration"] * 0.25
            + components["stability"] * 0.20
            + components["evaluation_depth"] * 0.10
            + components["context_fit"] * 0.10,
            6,
        )
        rationale.append(f"Composite performance-aware score is {score:.6f}.")
        return ModelPerformanceScore(
            model_id=model.model_id,
            score=score,
            components=components,
            rationale=tuple(rationale),
            warnings=tuple(warnings),
        )

    def rank_models(
        self,
        models: Iterable[RegisteredModelForSelection],
        context: ModelSelectionContext,
    ) -> tuple[ModelPerformanceScore, ...]:
        scores = [self.score_model(model, context) for model in models]
        return tuple(sorted(scores, key=lambda score: (-score.score, score.model_id)))

    def build_audit_record(
        self,
        *,
        selected_model_id: str,
        candidate_scores: tuple[ModelPerformanceScore, ...],
        context: ModelSelectionContext,
    ) -> ModelSelectionAuditRecord:
        return ModelSelectionAuditRecord(
            selected_model_id=selected_model_id,
            candidate_scores=candidate_scores,
            context=context,
        )

    def _context_fit(
        self,
        model: RegisteredModelForSelection,
        record: ModelPerformanceRecord | None,
        context: ModelSelectionContext,
    ) -> float:
        score = 0.0
        if context.forecast_type in model.supported_forecast_types:
            score += 0.4
        if context.forecast_days in model.supported_horizons_days:
            score += 0.3
        supported_contexts = record.supported_contexts if record else ()
        if any(key in supported_contexts for key in context.context_keys):
            score += 0.3
        return self._clamp(score)

    def _evaluation_depth(self, evaluation_count: int) -> float:
        if evaluation_count <= 0:
            return 0.0
        return self._clamp(evaluation_count / 100.0)

    def _clamp(self, value: float) -> float:
        return max(0.0, min(1.0, float(value)))
