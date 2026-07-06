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
    recent_accuracy: float | None = None
    horizon_accuracy: dict[int, float] = field(default_factory=dict)
    seasonal_accuracy: dict[str, float] = field(default_factory=dict)
    bias: float | None = None
    drift_score: float | None = None
    data_sufficiency: float | None = None

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["supported_contexts"] = list(self.supported_contexts)
        payload["horizon_accuracy"] = {str(key): value for key, value in self.horizon_accuracy.items()}
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
    item_id: str | None = None
    location_id: str | None = None
    category_id: str | None = None
    season_key: str | None = None
    event_tags: tuple[str, ...] = ()
    anomaly_state: str | None = None
    demand_pattern: str | None = None

    @property
    def context_keys(self) -> tuple[str, ...]:
        keys = [self.forecast_type, f"horizon:{self.forecast_days}"]
        if self.item_id:
            keys.append(f"item:{self.item_id}")
        if self.location_id:
            keys.append(f"location:{self.location_id}")
        if self.category_id:
            keys.append(f"category:{self.category_id}")
        if self.season_key:
            keys.append(f"season:{self.season_key}")
        if self.demand_pattern:
            keys.append(f"demand_pattern:{self.demand_pattern}")
        keys.extend(f"event:{tag}" for tag in self.event_tags)
        if self.anomaly_state:
            keys.append(f"anomaly:{self.anomaly_state}")
        if self.evidence_count == 0:
            keys.append("sparse_evidence")
        if self.feature_count > 0:
            keys.append("feature_backed")
        return tuple(keys)

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["event_tags"] = list(self.event_tags)
        return payload


@dataclass(frozen=True)
class AdaptiveRankingWeights:
    """Configurable score weights for Phase 7A adaptive model ranking."""

    accuracy: float = 0.24
    recent_accuracy: float = 0.16
    calibration: float = 0.11
    stability: float = 0.10
    bias_control: float = 0.08
    evaluation_depth: float = 0.07
    context_fit: float = 0.10
    horizon_fit: float = 0.06
    seasonality_fit: float = 0.04
    data_sufficiency: float = 0.02
    drift_resilience: float = 0.02

    def normalized(self) -> dict[str, float]:
        raw = asdict(self)
        total = sum(max(0.0, float(value)) for value in raw.values())
        if total <= 0:
            raise ValueError("Adaptive ranking weights must contain at least one positive value")
        return {key: max(0.0, float(value)) / total for key, value in raw.items()}

    def to_dict(self) -> dict[str, float]:
        return asdict(self)


@dataclass(frozen=True)
class AdaptiveRankingConfiguration:
    """Versioned configuration for adaptive model ranking decisions."""

    version: str = "7A.1"
    weights: AdaptiveRankingWeights = field(default_factory=AdaptiveRankingWeights)
    minimum_evaluation_depth: int = 30
    recency_half_life_days: int = 60

    def to_dict(self) -> dict[str, object]:
        return {
            "version": self.version,
            "weights": self.weights.to_dict(),
            "minimum_evaluation_depth": self.minimum_evaluation_depth,
            "recency_half_life_days": self.recency_half_life_days,
        }


@dataclass(frozen=True)
class ModelPerformanceScore:
    """Explainable score assigned to one eligible model candidate."""

    model_id: str
    score: float
    components: dict[str, float]
    rationale: tuple[str, ...]
    warnings: tuple[str, ...] = ()
    weight_version: str = "7A.1"

    def to_dict(self) -> dict[str, object]:
        return {
            "model_id": self.model_id,
            "score": self.score,
            "components": dict(self.components),
            "rationale": list(self.rationale),
            "warnings": list(self.warnings),
            "weight_version": self.weight_version,
        }


@dataclass(frozen=True)
class ModelSelectionAuditRecord:
    """Audit-safe record of a model selection decision."""

    selected_model_id: str
    candidate_scores: tuple[ModelPerformanceScore, ...]
    context: ModelSelectionContext
    ranking_configuration: AdaptiveRankingConfiguration = field(default_factory=AdaptiveRankingConfiguration)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, object]:
        return {
            "selected_model_id": self.selected_model_id,
            "candidate_scores": [score.to_dict() for score in self.candidate_scores],
            "context": self.context.to_dict(),
            "ranking_configuration": self.ranking_configuration.to_dict(),
            "created_at": self.created_at,
            "advisory_only": True,
            "read_only": True,
            "inventory_source_of_truth_preserved": True,
        }


class PerformanceAwareModelSelector:
    """Ranks eligible models using historical performance and request context."""

    def __init__(
        self,
        repository: ModelPerformanceRepository | None = None,
        *,
        ranking_configuration: AdaptiveRankingConfiguration | None = None,
    ) -> None:
        self._repository = repository or ModelPerformanceRepository()
        self._ranking_configuration = ranking_configuration or AdaptiveRankingConfiguration()

    @property
    def ranking_configuration(self) -> AdaptiveRankingConfiguration:
        return self._ranking_configuration

    def score_model(self, model: RegisteredModelForSelection, context: ModelSelectionContext) -> ModelPerformanceScore:
        record = self._repository.get(model.model_id)
        if self._uses_legacy_evidence(record):
            return self._legacy_score_model(model, context, record)
        return self._adaptive_score_model(model, context, record)

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
            ranking_configuration=self._ranking_configuration,
        )

    def _uses_legacy_evidence(self, record: ModelPerformanceRecord | None) -> bool:
        if self._ranking_configuration != AdaptiveRankingConfiguration():
            return False
        if record is None:
            return True
        return (
            record.recent_accuracy is None
            and not record.horizon_accuracy
            and not record.seasonal_accuracy
            and record.bias is None
            and record.drift_score is None
            and record.data_sufficiency is None
        )

    def _legacy_score_model(
        self,
        model: RegisteredModelForSelection,
        context: ModelSelectionContext,
        record: ModelPerformanceRecord | None,
    ) -> ModelPerformanceScore:
        warnings: list[str] = []
        rationale: list[str] = []
        if record is None:
            components = {
                "accuracy": 0.5,
                "calibration": 0.5,
                "stability": 0.5,
                "evaluation_depth": 0.0,
                "context_fit": self._legacy_context_fit(model, None, context),
            }
            warnings.append("No historical performance record exists for this model; neutral defaults were used.")
        else:
            components = {
                "accuracy": self._clamp(record.accuracy),
                "calibration": self._clamp(record.calibration),
                "stability": self._clamp(record.stability),
                "evaluation_depth": self._legacy_evaluation_depth(record.evaluation_count),
                "context_fit": self._legacy_context_fit(model, record, context),
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
            weight_version=self._ranking_configuration.version,
        )

    def _adaptive_score_model(
        self,
        model: RegisteredModelForSelection,
        context: ModelSelectionContext,
        record: ModelPerformanceRecord | None,
    ) -> ModelPerformanceScore:
        warnings: list[str] = []
        rationale: list[str] = []
        if record is None:
            components = {
                "accuracy": 0.5,
                "recent_accuracy": 0.5,
                "calibration": 0.5,
                "stability": 0.5,
                "bias_control": 0.5,
                "evaluation_depth": 0.0,
                "context_fit": self._context_fit(model, None, context),
                "horizon_fit": self._horizon_fit(model, None, context),
                "seasonality_fit": self._seasonality_fit(None, context),
                "data_sufficiency": 0.5,
                "drift_resilience": 0.5,
            }
            warnings.append("No historical performance record exists for this model; neutral defaults were used.")
        else:
            components = {
                "accuracy": self._clamp(record.accuracy),
                "recent_accuracy": self._recent_accuracy(record),
                "calibration": self._clamp(record.calibration),
                "stability": self._clamp(record.stability),
                "bias_control": self._bias_control(record),
                "evaluation_depth": self._evaluation_depth(record.evaluation_count),
                "context_fit": self._context_fit(model, record, context),
                "horizon_fit": self._horizon_fit(model, record, context),
                "seasonality_fit": self._seasonality_fit(record, context),
                "data_sufficiency": self._clamp(record.data_sufficiency if record.data_sufficiency is not None else self._evaluation_depth(record.evaluation_count)),
                "drift_resilience": self._drift_resilience(record),
            }
            rationale.append(
                f"Adaptive ranking used {record.evaluation_count} historical evaluation(s) for {model.model_name}."
            )
            if record.average_error is not None:
                rationale.append(f"Average recorded error is {record.average_error:.4f}.")
            if record.recent_accuracy is not None:
                rationale.append(f"Recent accuracy contribution is {components['recent_accuracy']:.4f}.")
            if context.context_keys:
                rationale.append(f"Context comparison considered {len(context.context_keys)} context key(s).")
        weights = self._ranking_configuration.weights.normalized()
        score = round(sum(components[key] * weights[key] for key in weights), 6)
        rationale.append(
            f"Adaptive model ranking score is {score:.6f} using weight configuration {self._ranking_configuration.version}."
        )
        return ModelPerformanceScore(
            model_id=model.model_id,
            score=score,
            components=components,
            rationale=tuple(rationale),
            warnings=tuple(warnings),
            weight_version=self._ranking_configuration.version,
        )

    def _legacy_context_fit(
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

    def _context_fit(
        self,
        model: RegisteredModelForSelection,
        record: ModelPerformanceRecord | None,
        context: ModelSelectionContext,
    ) -> float:
        score = 0.0
        if context.forecast_type in model.supported_forecast_types:
            score += 0.25
        supported_contexts = set(record.supported_contexts if record else ())
        if supported_contexts:
            matched = sum(1 for key in context.context_keys if key in supported_contexts)
            score += min(0.75, matched / max(len(context.context_keys), 1))
        elif context.forecast_days in model.supported_horizons_days:
            score += 0.25
        return self._clamp(score)

    def _horizon_fit(
        self,
        model: RegisteredModelForSelection,
        record: ModelPerformanceRecord | None,
        context: ModelSelectionContext,
    ) -> float:
        if record and context.forecast_days in record.horizon_accuracy:
            return self._clamp(record.horizon_accuracy[context.forecast_days])
        if context.forecast_days in model.supported_horizons_days:
            return 1.0
        nearest = min((abs(context.forecast_days - horizon) for horizon in model.supported_horizons_days), default=999)
        if nearest <= 7:
            return 0.7
        if nearest <= 30:
            return 0.4
        return 0.0

    def _seasonality_fit(self, record: ModelPerformanceRecord | None, context: ModelSelectionContext) -> float:
        if not context.season_key:
            return 0.5
        if not record or not record.seasonal_accuracy:
            return 0.5
        return self._clamp(record.seasonal_accuracy.get(context.season_key, 0.35))

    def _recent_accuracy(self, record: ModelPerformanceRecord) -> float:
        base = self._clamp(record.recent_accuracy if record.recent_accuracy is not None else record.accuracy)
        recency = self._recency_factor(record.last_evaluated_at)
        return self._clamp((base * 0.85) + (recency * 0.15))

    def _recency_factor(self, last_evaluated_at: str | None) -> float:
        if not last_evaluated_at:
            return 0.5
        try:
            evaluated_at = datetime.fromisoformat(last_evaluated_at.replace("Z", "+00:00"))
        except ValueError:
            return 0.5
        if evaluated_at.tzinfo is None:
            evaluated_at = evaluated_at.replace(tzinfo=timezone.utc)
        age_days = max(0.0, (datetime.now(timezone.utc) - evaluated_at).total_seconds() / 86400)
        half_life = max(1, self._ranking_configuration.recency_half_life_days)
        return self._clamp(0.5 ** (age_days / half_life))

    def _bias_control(self, record: ModelPerformanceRecord) -> float:
        if record.bias is None:
            return 0.5
        return self._clamp(1.0 - abs(record.bias))

    def _drift_resilience(self, record: ModelPerformanceRecord) -> float:
        if record.drift_score is None:
            return 0.5
        return self._clamp(1.0 - record.drift_score)

    def _legacy_evaluation_depth(self, evaluation_count: int) -> float:
        if evaluation_count <= 0:
            return 0.0
        return self._clamp(evaluation_count / 100.0)

    def _evaluation_depth(self, evaluation_count: int) -> float:
        if evaluation_count <= 0:
            return 0.0
        return self._clamp(evaluation_count / max(1, self._ranking_configuration.minimum_evaluation_depth))

    def _clamp(self, value: float) -> float:
        return max(0.0, min(1.0, float(value)))
