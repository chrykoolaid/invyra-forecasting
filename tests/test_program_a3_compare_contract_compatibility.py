from __future__ import annotations

from invyra_forecasting.api.app import _comparison_candidate


def test_comparison_candidate_accepts_legacy_confidence_score_field() -> None:
    candidate = _comparison_candidate(
        {
            "forecast": {"method": "moving_average", "forecast_quantity": 12.0},
            "confidence": {"score": 0.75},
            "explanation": {"summary": "test"},
            "audit_event": {"details": {"evidence_refs": ["evidence-1"]}},
        }
    )

    assert candidate["confidence_score"] == 0.75
    assert candidate["model_id"] == "moving_average"
    assert candidate["evidence_refs"] == ["evidence-1"]


def test_comparison_candidate_accepts_enterprise_confidence_score_field() -> None:
    candidate = _comparison_candidate(
        {
            "forecast": {"model_name": "adaptive", "forecast_quantity": 15.0},
            "confidence": {"confidence_score": 0.82},
            "explanation": {"summary": "test"},
            "audit_event": {"details": {}},
        }
    )

    assert candidate["confidence_score"] == 0.82
    assert candidate["model_id"] == "adaptive"
    assert candidate["evidence_refs"] == []
