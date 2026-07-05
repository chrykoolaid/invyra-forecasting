from __future__ import annotations

from dataclasses import replace

import pytest

from invyra_forecasting.constants import Environment
from invyra_forecasting.intelligence.evidence import EvidenceScoringServiceV2, EvidenceStrength
from invyra_forecasting.intelligence.objects import (
    EvidenceLink,
    ForecastFeatureSet,
    ForecastIntelligence,
    SignalQualityAssessment,
    WeightedForecastSignal,
)
from invyra_forecasting.signals.schema import (
    ForecastSignal,
    ForecastSignalDirection,
    ForecastSignalSource,
    ForecastSignalType,
)


def _signal(signal_id: str, evidence_ref: str, confidence: float = 1.0) -> ForecastSignal:
    return ForecastSignal.create(
        signal_type=ForecastSignalType.SALE_EVENT,
        module_source=ForecastSignalSource.POS,
        item_id="item-1",
        sku="SKU-1",
        location_id="location-1",
        quantity=10.0,
        unit="pcs",
        direction=ForecastSignalDirection.OUTBOUND,
        confidence=confidence,
        evidence_ref=evidence_ref,
        signal_id=signal_id,
    )


def _intelligence() -> ForecastIntelligence:
    strong_signal = _signal("signal-strong", "evidence-strong", confidence=0.95)
    weak_signal = _signal("signal-weak", "evidence-weak", confidence=0.60)
    strong_quality = SignalQualityAssessment(
        signal_id="signal-strong",
        score=0.95,
        freshness_score=0.90,
        completeness_score=0.95,
        reliability_score=0.90,
    )
    weak_quality = SignalQualityAssessment(
        signal_id="signal-weak",
        score=0.45,
        freshness_score=0.50,
        completeness_score=0.40,
        reliability_score=0.45,
        issues=("missing_supplier_context",),
    )
    strong_weighted = WeightedForecastSignal(strong_signal, strong_quality, weight=0.90)
    weak_weighted = WeightedForecastSignal(weak_signal, weak_quality, weight=0.35)
    return ForecastIntelligence(
        item_id="item-1",
        location_id="location-1",
        environment=Environment.TRAINING,
        analysis_window_days=30,
        normalized_signals=(strong_signal, weak_signal),
        quality_assessments=(strong_quality, weak_quality),
        weighted_signals=(strong_weighted, weak_weighted),
        features=ForecastFeatureSet(item_id="item-1", location_id="location-1", analysis_window_days=30, signal_count=2),
        evidence_links=(
            EvidenceLink("signal-strong", "evidence-strong", "POS", "SALE_EVENT"),
            EvidenceLink("signal-weak", "evidence-weak", "POS", "SALE_EVENT"),
        ),
        confidence=0.82,
        audit_refs=("audit-1",),
    )


def test_phase_6e_scores_real_intelligence_evidence() -> None:
    summary = EvidenceScoringServiceV2().score_intelligence(_intelligence())

    assert summary.item_id == "item-1"
    assert summary.location_id == "location-1"
    assert summary.evidence_count == 2
    assert summary.strongest_evidence_refs[0] == "evidence-strong"
    assert summary.weakest_evidence_refs[0] == "evidence-weak"
    assert summary.scores[0].strength == EvidenceStrength.STRONG
    assert summary.scores[1].strength == EvidenceStrength.WEAK
    assert summary.advisory_only is True
    assert summary.read_only is True
    assert summary.inventory_source_of_truth_preserved is True


def test_phase_6e_score_components_are_explainable() -> None:
    summary = EvidenceScoringServiceV2().score_intelligence(_intelligence())
    score = summary.scores[0]

    assert set(score.components) == {
        "signal_weight",
        "quality",
        "freshness",
        "completeness",
        "reliability",
        "traceability",
    }
    assert score.components["traceability"] == 1.0
    assert any("Signal weight" in reason for reason in score.rationale)
    assert score.to_dict()["strength"] == "STRONG"


def test_phase_6e_scores_unmatched_evidence_as_limited_but_traceable() -> None:
    service = EvidenceScoringServiceV2()
    link = EvidenceLink("missing-signal", "evidence-only", "POS", "SALE_EVENT")

    score = service.score_link(link, None)

    assert score.score == 0.05
    assert score.strength == EvidenceStrength.WEAK
    assert score.components["traceability"] == 1.0
    assert any("no weighted signal" in reason for reason in score.rationale)


def test_phase_6e_empty_evidence_summary_is_safe() -> None:
    intelligence = replace(_intelligence(), evidence_links=())

    summary = EvidenceScoringServiceV2().score_intelligence(intelligence)

    assert summary.evidence_count == 0
    assert summary.average_score == 0.0
    assert summary.strongest_evidence_refs == ()
    assert summary.weakest_evidence_refs == ()


def test_phase_6e_rejects_non_advisory_scores() -> None:
    score = EvidenceScoringServiceV2().score_intelligence(_intelligence()).scores[0]

    with pytest.raises(ValueError, match="evidence scores must remain advisory-only"):
        replace(score, advisory_only=False)
