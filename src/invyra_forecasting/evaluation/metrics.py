from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class ForecastPrediction:
    forecast_id: str
    item_id: str
    location_id: str
    model_name: str
    model_version: str
    forecast_horizon_days: int
    predicted_quantity: float
    confidence: float
    generated_at_utc: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.forecast_horizon_days < 1:
            raise ValueError("forecast_horizon_days must be 1 or greater")
        if self.predicted_quantity < 0:
            raise ValueError("predicted_quantity must not be negative")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ForecastOutcome:
    forecast_id: str
    actual_quantity: float
    outcome_timestamp_utc: str | None = None
    outcome_source: str = "ledger_observed_outcome"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.actual_quantity < 0:
            raise ValueError("actual_quantity must not be negative")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ForecastEvaluationResult:
    forecast_id: str
    item_id: str
    location_id: str
    model_name: str
    model_version: str
    predicted_quantity: float
    actual_quantity: float
    forecast_error: float
    absolute_error: float
    squared_error: float
    absolute_percentage_error: float | None
    bias: float
    accuracy_score: float
    confidence: float
    calibration_gap: float
    evaluation_metadata: dict[str, Any] = field(default_factory=dict)
    advisory_only: bool = True
    read_only: bool = True
    inventory_source_of_truth_preserved: bool = True

    def __post_init__(self) -> None:
        if not self.advisory_only:
            raise ValueError("forecast evaluation must remain advisory-only")
        if not self.read_only:
            raise ValueError("forecast evaluation must remain read-only")
        if not self.inventory_source_of_truth_preserved:
            raise ValueError("inventory source of truth must be preserved")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ForecastEvaluationService:
    """Read-only forecast performance evaluator."""

    def evaluate(self, prediction: ForecastPrediction, outcome: ForecastOutcome) -> ForecastEvaluationResult:
        if prediction.forecast_id != outcome.forecast_id:
            raise ValueError("prediction and outcome forecast_id must match")
        error = outcome.actual_quantity - prediction.predicted_quantity
        absolute_error = abs(error)
        squared_error = error**2
        absolute_percentage_error = None if outcome.actual_quantity == 0 else absolute_error / outcome.actual_quantity
        accuracy_score = self._accuracy_score(absolute_error, outcome.actual_quantity)
        calibration_gap = abs(prediction.confidence - accuracy_score)
        return ForecastEvaluationResult(
            forecast_id=prediction.forecast_id,
            item_id=prediction.item_id,
            location_id=prediction.location_id,
            model_name=prediction.model_name,
            model_version=prediction.model_version,
            predicted_quantity=prediction.predicted_quantity,
            actual_quantity=outcome.actual_quantity,
            forecast_error=round(error, 4),
            absolute_error=round(absolute_error, 4),
            squared_error=round(squared_error, 4),
            absolute_percentage_error=None if absolute_percentage_error is None else round(absolute_percentage_error, 4),
            bias=round(error, 4),
            accuracy_score=round(accuracy_score, 4),
            confidence=prediction.confidence,
            calibration_gap=round(calibration_gap, 4),
            evaluation_metadata={
                "forecast_horizon_days": prediction.forecast_horizon_days,
                "outcome_source": outcome.outcome_source,
            },
        )

    def evaluate_many(
        self,
        pairs: tuple[tuple[ForecastPrediction, ForecastOutcome], ...],
    ) -> tuple[ForecastEvaluationResult, ...]:
        return tuple(self.evaluate(prediction, outcome) for prediction, outcome in pairs)

    def summarize(self, results: tuple[ForecastEvaluationResult, ...]) -> dict[str, Any]:
        if not results:
            return {
                "count": 0,
                "mae": None,
                "rmse": None,
                "mape": None,
                "bias": None,
                "average_accuracy_score": None,
            }
        count = len(results)
        mae = sum(result.absolute_error for result in results) / count
        rmse = (sum(result.squared_error for result in results) / count) ** 0.5
        ape_values = [result.absolute_percentage_error for result in results if result.absolute_percentage_error is not None]
        mape = None if not ape_values else sum(ape_values) / len(ape_values)
        bias = sum(result.bias for result in results) / count
        accuracy = sum(result.accuracy_score for result in results) / count
        return {
            "count": count,
            "mae": round(mae, 4),
            "rmse": round(rmse, 4),
            "mape": None if mape is None else round(mape, 4),
            "bias": round(bias, 4),
            "average_accuracy_score": round(accuracy, 4),
        }

    def _accuracy_score(self, absolute_error: float, actual_quantity: float) -> float:
        denominator = max(actual_quantity, 1.0)
        return max(0.0, min(1.0, 1.0 - (absolute_error / denominator)))
