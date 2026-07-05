from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any

from invyra_forecasting.intelligence.objects import EvidenceLink, ForecastIntelligence, WeightedForecastSignal


class EvidenceStrength(StrEnum):
    WEAK = "WEAK"
    MODERATE = "MODERATE"
    STRONG = "STRONG"


@dataclass(frozen=True)
class EvidenceScoreV2:
    signal_id: str
    evidence_ref: str
    module_source: str
    signal_type: str
    score: float
    strength: EvidenceStrength
    components: dict[str, float]
    rationale: tuple[str, ...]
    advisory_only: bool = True
    read_only: bool = True
    inventory_source_of_truth_preserved: bool = True

    def __post_init__(self) -> None:
        if not self.signal_id:
            raise ValueError("signal_id is required")
        if not self.evidence_ref:
            raise ValueError("evidence_ref is required")
        if not self.advisory_only:
            raise ValueError("evidence scores must remain advisory-only")
        if not self.read_only:
            raise ValueError("evidence scores must remain read-only")
        if not self.inventory_source_of_truth_preserved:
            raise ValueError("inventory source of truth must be preserved")
        if not 0.0 <= self.score <= 1.0:
            raise ValueError("score must be between 0.0 and 1.0")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["strength"] = self.strength.value
        payload["rationale"] = list(self.rationale)
        payload["components"] = dict(self.components)
        return payload


@dataclass(frozen=True)
class EvidenceScoreSummaryV2:
    item_id: str
    location_id: str
    evidence_count: int
    average_score: float
    strongest_evidence_refs: tuple[str, ...]
    weakest_evidence_refs: tuple[str, ...]
    scores: tuple[EvidenceScoreV2, ...]
    advisory_only: bool = True
    read_only: bool = True
    inventory_source_of_truth_preserved: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.advisory_only:
            raise ValueError("evidence score summaries must remain advisory-only")
        if not self.read_only:
            raise ValueError("evidence score summaries must remain read-only")
        if not self.inventory_source_of_truth_preserved:
            raise ValueError("inventory source of truth must be preserved")

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "location_id": self.location_id,
            "evidence_count": self.evidence_count,
            "average_score": self.average_score,
            "strongest_evidence_refs": list(self.strongest_evidence_refs),
            "weakest_evidence_refs": list(self.weakest_evidence_refs),
            "scores": [score.to_dict() for score in self.scores],
            "advisory_only": self.advisory_only,
            "read_only": self.read_only,
            "inventory_source_of_truth_preserved": self.inventory_source_of_truth_preserved,
            "metadata": dict(self.metadata),
        }


class EvidenceScoringServiceV2:
    def score_intelligence(self, intelligence: ForecastIntelligence) -> EvidenceScoreSummaryV2:
        weighted_by_signal_id = {weighted.signal.signal_id: weighted for weighted in intelligence.weighted_signals}
        scores = tuple(
            self.score_link(link, weighted_by_signal_id.get(link.signal_id))
            for link in intelligence.evidence_links
        )
        ordered = tuple(sorted(scores, key=lambda score: (-score.score, score.evidence_ref)))
        average_score = 0.0 if not scores else round(sum(score.score for score in scores) / len(scores), 6)
        strongest = tuple(score.evidence_ref for score in ordered[:3])
        weakest = tuple(score.evidence_ref for score in reversed(ordered[-3:]))
        return EvidenceScoreSummaryV2(
            item_id=intelligence.item_id,
            location_id=intelligence.location_id,
            evidence_count=len(scores),
            average_score=average_score,
            strongest_evidence_refs=strongest,
            weakest_evidence_refs=weakest,
            scores=ordered,
            metadata={
                "analysis_window_days": intelligence.analysis_window_days,
                "intelligence_confidence": intelligence.confidence,
                "audit_refs": list(intelligence.audit_refs),
            },
        )

    def score_link(self, link: EvidenceLink, weighted: WeightedForecastSignal | None) -> EvidenceScoreV2:
        if weighted is None:
            components = {
                "signal_weight": 0.0,
                "quality": 0.0,
                "freshness": 0.0,
                "completeness": 0.0,
                "reliability": 0.0,
                "traceability": 1.0,
            }
            rationale = (
                "Evidence link is traceable but no weighted signal was available.",
                "Score is limited because signal quality and weight could not be verified.",
            )
        else:
            quality = weighted.quality
            components = {
                "signal_weight": self._clamp(weighted.weight),
                "quality": self._clamp(quality.score),
                "freshness": self._clamp(quality.freshness_score),
                "completeness": self._clamp(quality.completeness_score),
                "reliability": self._clamp(quality.reliability_score),
                "traceability": 1.0 if link.evidence_ref else 0.0,
            }
            rationale = (
                f"Signal weight is {weighted.weight:.4f} based on confidence, quality, and signal type.",
                f"Quality score is {quality.score:.4f} with {len(quality.issues)} quality issue(s).",
                "Evidence reference is traceable to the originating signal.",
            )
        score = round(
            components["signal_weight"] * 0.30
            + components["quality"] * 0.25
            + components["freshness"] * 0.15
            + components["completeness"] * 0.15
            + components["reliability"] * 0.10
            + components["traceability"] * 0.05,
            6,
        )
        return EvidenceScoreV2(
            signal_id=link.signal_id,
            evidence_ref=link.evidence_ref,
            module_source=link.module_source,
            signal_type=link.signal_type,
            score=score,
            strength=self._strength(score),
            components=components,
            rationale=rationale,
        )

    def _strength(self, score: float) -> EvidenceStrength:
        if score >= 0.80:
            return EvidenceStrength.STRONG
        if score >= 0.50:
            return EvidenceStrength.MODERATE
        return EvidenceStrength.WEAK

    def _clamp(self, value: float) -> float:
        return max(0.0, min(1.0, float(value)))
