from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class EvidenceImpact(StrEnum):
    VERY_HIGH = "VERY_HIGH"
    HIGH = "HIGH"
    MODERATE = "MODERATE"
    LOW = "LOW"
    VERY_LOW = "VERY_LOW"


@dataclass(frozen=True)
class RankedEvidenceItem:
    rank: int
    signal_id: str
    evidence_ref: str | None
    module_source: str
    signal_type: str
    relevance_score: float
    reliability_score: float
    completeness_score: float
    business_impact_score: float
    confidence_contribution: float
    overall_score: float
    impact: EvidenceImpact
    direction: str = "supporting"
    explanation: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.rank < 1:
            raise ValueError("rank must be 1 or greater")
        for value in (
            self.relevance_score,
            self.reliability_score,
            self.completeness_score,
            self.business_impact_score,
            self.confidence_contribution,
            self.overall_score,
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError("score values must be between 0.0 and 1.0")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["impact"] = self.impact.value
        return payload


@dataclass(frozen=True)
class EvidenceRankingResult:
    ranked_evidence: tuple[RankedEvidenceItem, ...]
    positive_evidence: tuple[RankedEvidenceItem, ...]
    negative_evidence: tuple[RankedEvidenceItem, ...]
    explanation_summary: tuple[str, ...]
    advisory_only: bool = True
    inventory_source_of_truth_preserved: bool = True

    def __post_init__(self) -> None:
        if not self.advisory_only:
            raise ValueError("ranking must remain advisory-only")
        if not self.inventory_source_of_truth_preserved:
            raise ValueError("inventory source of truth must be preserved")

    def to_dict(self) -> dict[str, Any]:
        return {
            "ranked_evidence": [item.to_dict() for item in self.ranked_evidence],
            "positive_evidence": [item.to_dict() for item in self.positive_evidence],
            "negative_evidence": [item.to_dict() for item in self.negative_evidence],
            "explanation_summary": list(self.explanation_summary),
            "advisory_only": self.advisory_only,
            "inventory_source_of_truth_preserved": self.inventory_source_of_truth_preserved,
        }


class EvidenceRankingService:
    def rank(self, ranked_items: tuple[RankedEvidenceItem, ...]) -> EvidenceRankingResult:
        ranked = tuple(
            RankedEvidenceItem(
                rank=index,
                signal_id=item.signal_id,
                evidence_ref=item.evidence_ref,
                module_source=item.module_source,
                signal_type=item.signal_type,
                relevance_score=item.relevance_score,
                reliability_score=item.reliability_score,
                completeness_score=item.completeness_score,
                business_impact_score=item.business_impact_score,
                confidence_contribution=item.confidence_contribution,
                overall_score=item.overall_score,
                impact=item.impact,
                direction=item.direction,
                explanation=item.explanation,
                metadata=item.metadata,
            )
            for index, item in enumerate(sorted(ranked_items, key=lambda item: item.overall_score, reverse=True), start=1)
        )
        return EvidenceRankingResult(
            ranked_evidence=ranked,
            positive_evidence=tuple(item for item in ranked if item.direction == "supporting"),
            negative_evidence=tuple(item for item in ranked if item.direction == "reducing_confidence"),
            explanation_summary=("Evidence items ranked for advisory explainability.",),
        )
