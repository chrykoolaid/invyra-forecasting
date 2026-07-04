from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any

from invyra_forecasting.intelligence.objects import ForecastIntelligence
from invyra_forecasting.models.orchestration import OrchestratedForecastResult


class ConfidenceBand(StrEnum):
    """Business-friendly confidence band."""

    VERY_HIGH = "VERY_HIGH"
    HIGH = "HIGH"
    MODERATE = "MODERATE"
    LOW = "LOW"
    VERY_LOW = "VERY_LOW"


@dataclass(frozen=True)
class ConfidenceDimensionScores:
    """Structured confidence dimensions used to calibrate forecast trust."""

    data_confidence: float
    feature_confidence: float
    evidence_confidence: float
    model_confidence: float
    context_confidence: float
    stability_confidence: float

    def __post_init__(self) -> None:
        for value in self.to_dict().values():
            if not 0.0 <= value <= 1.0:
                raise ValueError("confidence dimension scores must be between 0.0 and 1.0")

    def overall(self) -> float:
        scores = tuple(self.to_dict().values())
        return round(sum(scores) / len(scores), 4)

    def to_dict(self) -> dict[str, float]:
        return asdict(self)


@dataclass(frozen=True)
class CalibratedConfidence:
    """Explainable calibrated confidence result.

    Calibration is advisory-only. It does not change inventory, stock movements,
    purchase orders, ledger truth, or the underlying forecast quantity.
    """

    overall_confidence: float
    band: ConfidenceBand
    dimensions: ConfidenceDimensionScores
    positive_factors: tuple[str, ...] = ()
    negative_factors: tuple[str, ...] = ()
    improvement_guidance: tuple[str, ...] = ()
    calibration_metadata: dict[str, Any] = field(default_factory=dict)
    advisory_only: bool = True
    inventory_source_of_truth_preserved: bool = True

    def __post_init__(self) -> None:
        if not 0.0 <= self.overall_confidence <= 1.0:
            raise ValueError("overall_confidence must be between 0.0 and 1.0")
        if not self.advisory_only:
            raise ValueError("confidence calibration must remain advisory-only")
        if not self.inventory_source_of_truth_preserved:
            raise ValueError("inventory source of truth must be preserved")

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall_confidence": self.overall_confidence,
            "band": self.band.value,
            "dimensions": self.dimensions.to_dict(),
            "positive_factors": list(self.positive_factors),
            "negative_factors": list(self.negative_factors),
            "improvement_guidance": list(self.improvement_guidance),
            "calibration_metadata": dict(self.calibration_metadata),
            "advisory_only": self.advisory_only,
            "inventory_source_of_truth_preserved": self.inventory_source_of_truth_preserved,
        }


class ConfidenceCalibrationService:
    """Calibrates forecast confidence using explainable dimensions."""

    def calibrate(
        self,
        intelligence: ForecastIntelligence,
        forecast_result: OrchestratedForecastResult,
    ) -> CalibratedConfidence:
        dimensions = self._score_dimensions(intelligence, forecast_result)
        overall = dimensions.overall()
        return CalibratedConfidence(
            overall_confidence=overall,
            band=self._band(overall),
            dimensions=dimensions,
            positive_factors=self._positive_factors(intelligence, forecast_result, dimensions),
            negative_factors=self._negative_factors(intelligence, forecast_result, dimensions),
            improvement_guidance=self._improvement_guidance(dimensions),
            calibration_metadata={
                "source_confidence": intelligence.confidence,
                "selected_model": forecast_result.selection.selected_model.model_name,
                "selected_model_version": forecast_result.selection.selected_model.model_version,
                "forecast_days": forecast_result.model_output.forecast_days,
                "forecast_quantity_unchanged": forecast_result.model_output.forecast_quantity,
            },
            advisory_only=forecast_result.advisory_only,
            inventory_source_of_truth_preserved=forecast_result.inventory_source_of_truth_preserved,
        )

    def _score_dimensions(
        self,
        intelligence: ForecastIntelligence,
        forecast_result: OrchestratedForecastResult,
    ) -> ConfidenceDimensionScores:
        data_confidence = self._clamp(intelligence.confidence)
        signal_count = intelligence.features.signal_count
        engineered_count = int(forecast_result.model_output.to_dict().get("feature_summary", {}).get("engineered_feature_count", 0))
        # Model output does not expose feature_summary directly, so fall back to signal availability.
        feature_confidence = self._clamp(min(1.0, max(intelligence.confidence, signal_count / 5 if signal_count else 0.5)))
        evidence_confidence = 1.0 if intelligence.evidence_links or intelligence.audit_refs else 0.5
        model_confidence = 0.85 if forecast_result.selection.selected_model.status.value == "PRODUCTION" else 0.7
        context_confidence = 0.9 if intelligence.features.latest_on_hand is not None else 0.65
        stability_confidence = 0.8 if forecast_result.model_output.stockout_risk != "UNKNOWN" else 0.6
        if engineered_count:
            feature_confidence = max(feature_confidence, min(1.0, engineered_count / 10))
        return ConfidenceDimensionScores(
            data_confidence=round(data_confidence, 4),
            feature_confidence=round(feature_confidence, 4),
            evidence_confidence=round(evidence_confidence, 4),
            model_confidence=round(model_confidence, 4),
            context_confidence=round(context_confidence, 4),
            stability_confidence=round(stability_confidence, 4),
        )

    def _band(self, score: float) -> ConfidenceBand:
        if score >= 0.9:
            return ConfidenceBand.VERY_HIGH
        if score >= 0.75:
            return ConfidenceBand.HIGH
        if score >= 0.55:
            return ConfidenceBand.MODERATE
        if score >= 0.35:
            return ConfidenceBand.LOW
        return ConfidenceBand.VERY_LOW

    def _positive_factors(
        self,
        intelligence: ForecastIntelligence,
        forecast_result: OrchestratedForecastResult,
        dimensions: ConfidenceDimensionScores,
    ) -> tuple[str, ...]:
        factors: list[str] = []
        if dimensions.data_confidence >= 0.75:
            factors.append("Signal quality supports the forecast.")
        if dimensions.evidence_confidence >= 0.75:
            factors.append("Evidence or audit references are available.")
        if forecast_result.selection.selected_model.status.value == "PRODUCTION":
            factors.append("Selected model is approved for production orchestration.")
        if intelligence.features.latest_on_hand is not None:
            factors.append("On-hand inventory context is available.")
        return tuple(factors)

    def _negative_factors(
        self,
        intelligence: ForecastIntelligence,
        forecast_result: OrchestratedForecastResult,
        dimensions: ConfidenceDimensionScores,
    ) -> tuple[str, ...]:
        factors: list[str] = []
        if dimensions.data_confidence < 0.75:
            factors.append("Signal quality reduces forecast confidence.")
        if not intelligence.evidence_links and not intelligence.audit_refs:
            factors.append("Evidence references are limited or missing.")
        if forecast_result.model_output.stockout_risk == "UNKNOWN":
            factors.append("Stockout risk is unknown due to missing demand or on-hand context.")
        if intelligence.features.latest_on_hand is None:
            factors.append("On-hand inventory context is unavailable.")
        return tuple(factors)

    def _improvement_guidance(self, dimensions: ConfidenceDimensionScores) -> tuple[str, ...]:
        guidance: list[str] = []
        if dimensions.data_confidence < 0.75:
            guidance.append("Improve signal completeness and quality to raise confidence.")
        if dimensions.evidence_confidence < 0.75:
            guidance.append("Attach stronger evidence references to future forecast inputs.")
        if dimensions.context_confidence < 0.75:
            guidance.append("Provide recent on-hand inventory context to improve forecast certainty.")
        if dimensions.stability_confidence < 0.75:
            guidance.append("More stable demand and coverage history would improve confidence.")
        return tuple(guidance)

    def _clamp(self, value: float) -> float:
        return min(1.0, max(0.0, value))
