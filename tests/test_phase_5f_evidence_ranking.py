import pytest

from invyra_forecasting.evidence import EvidenceImpact, EvidenceRankingService, RankedEvidenceItem
from invyra_forecasting.evidence.ranking import EvidenceRankingResult


def _item(signal_id: str, score: float, direction: str = "supporting") -> RankedEvidenceItem:
    return RankedEvidenceItem(
        rank=1,
        signal_id=signal_id,
        evidence_ref=f"evidence::{signal_id}",
        module_source="INVENTORY",
        signal_type="SALE_EVENT",
        relevance_score=score,
        reliability_score=score,
        completeness_score=score,
        business_impact_score=score,
        confidence_contribution=score,
        overall_score=score,
        impact=EvidenceImpact.HIGH if score >= 0.75 else EvidenceImpact.MODERATE,
        direction=direction,
        explanation=f"{signal_id} supports advisory explainability.",
    )


def test_ranked_evidence_item_validates_score_range():
    with pytest.raises(ValueError):
        _item("S1", 1.2)


def test_ranked_evidence_item_requires_positive_rank():
    with pytest.raises(ValueError):
        RankedEvidenceItem(
            rank=0,
            signal_id="S1",
            evidence_ref="evidence::S1",
            module_source="INVENTORY",
            signal_type="SALE_EVENT",
            relevance_score=0.8,
            reliability_score=0.8,
            completeness_score=0.8,
            business_impact_score=0.8,
            confidence_contribution=0.8,
            overall_score=0.8,
            impact=EvidenceImpact.HIGH,
        )


def test_evidence_ranking_orders_by_overall_score():
    result = EvidenceRankingService().rank((_item("LOW", 0.6), _item("HIGH", 0.9)))

    assert result.ranked_evidence[0].signal_id == "HIGH"
    assert result.ranked_evidence[0].rank == 1
    assert result.ranked_evidence[1].signal_id == "LOW"
    assert result.ranked_evidence[1].rank == 2


def test_evidence_ranking_separates_positive_and_negative_evidence():
    result = EvidenceRankingService().rank((_item("P", 0.8), _item("N", 0.4, "reducing_confidence")))

    assert len(result.positive_evidence) == 1
    assert len(result.negative_evidence) == 1
    assert result.negative_evidence[0].signal_id == "N"


def test_evidence_ranking_result_serializes_and_preserves_guardrails():
    result = EvidenceRankingService().rank((_item("S1", 0.9),))
    payload = result.to_dict()

    assert payload["ranked_evidence"][0]["impact"] == "HIGH"
    assert payload["advisory_only"] is True
    assert payload["inventory_source_of_truth_preserved"] is True


def test_evidence_ranking_result_rejects_guardrail_drift():
    with pytest.raises(ValueError):
        EvidenceRankingResult(
            ranked_evidence=(),
            positive_evidence=(),
            negative_evidence=(),
            explanation_summary=(),
            advisory_only=False,
        )
