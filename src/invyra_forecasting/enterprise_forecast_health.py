from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

from invyra_forecasting.enterprise_intelligence_summary import EnterpriseForecastIntelligenceSummary

ENTERPRISE_FORECAST_HEALTH_SCHEMA_VERSION = "1.0.0"


class EnterpriseForecastHealthStatus(str, Enum):
    UNAVAILABLE = "unavailable"
    LIMITED = "limited"
    DEVELOPING = "developing"
    HEALTHY = "healthy"
    STRONG = "strong"


@dataclass(frozen=True)
class EnterpriseForecastHealth:
    namespace: str
    as_of_utc: str
    health_status: EnterpriseForecastHealthStatus
    evaluated_coverage_ratio: float
    model_version_count: int
    evaluated_model_version_count: int
    total_eligible_evaluation_count: int
    weighted_average_accuracy_score: float | None
    weighted_average_calibration_gap: float | None
    classification_reasons: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    schema_version: str = ENTERPRISE_FORECAST_HEALTH_SCHEMA_VERSION
    advisory_only: bool = True
    read_only: bool = True
    inventory_source_of_truth_preserved: bool = True

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["health_status"] = self.health_status.value
        payload["classification_reasons"] = list(self.classification_reasons)
        payload["evidence_refs"] = list(self.evidence_refs)
        return payload


class EnterpriseForecastHealthPolicy:
    """Classifies portfolio evidence health without scoring models or recommending action."""

    def classify(self, summary: EnterpriseForecastIntelligenceSummary) -> EnterpriseForecastHealth:
        count = summary.model_version_count
        evaluated = summary.evaluated_model_version_count
        coverage = 0.0 if count == 0 else round(evaluated / count, 4)
        accuracy = summary.weighted_average_accuracy_score
        calibration = summary.weighted_average_calibration_gap

        if count == 0 or evaluated == 0:
            status = EnterpriseForecastHealthStatus.UNAVAILABLE
            reasons = ("no certified portfolio evaluation evidence available",)
        elif coverage < 0.5:
            status = EnterpriseForecastHealthStatus.LIMITED
            reasons = ("fewer than half of registered model versions have certified evidence",)
        elif accuracy is None or calibration is None:
            status = EnterpriseForecastHealthStatus.DEVELOPING
            reasons = ("portfolio coverage exists but certified quality metrics are incomplete",)
        elif coverage == 1.0 and accuracy >= 0.9 and calibration <= 0.1:
            status = EnterpriseForecastHealthStatus.STRONG
            reasons = ("full evaluated coverage with high accuracy and low calibration gap",)
        elif coverage >= 0.75 and accuracy >= 0.8 and calibration <= 0.2:
            status = EnterpriseForecastHealthStatus.HEALTHY
            reasons = ("broad evaluated coverage with acceptable accuracy and calibration",)
        else:
            status = EnterpriseForecastHealthStatus.DEVELOPING
            reasons = ("certified evidence exists but portfolio quality thresholds are not yet met",)

        refs = tuple(sorted({ref for model in summary.models for ref in model.evidence_refs}))
        return EnterpriseForecastHealth(
            namespace=summary.namespace,
            as_of_utc=summary.as_of_utc,
            health_status=status,
            evaluated_coverage_ratio=coverage,
            model_version_count=count,
            evaluated_model_version_count=evaluated,
            total_eligible_evaluation_count=summary.total_eligible_evaluation_count,
            weighted_average_accuracy_score=accuracy,
            weighted_average_calibration_gap=calibration,
            classification_reasons=reasons,
            evidence_refs=refs,
        )
