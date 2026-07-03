from invyra_forecasting.explanation import (
    enrich_explanation_with_intelligence_context,
    intelligence_context_drivers,
    intelligence_context_warnings,
)
from invyra_forecasting.schemas import ExplanationResult


def test_intelligence_context_builds_explanation_drivers():
    context = {
        "signal_count": 2,
        "confidence": 0.75,
        "feature_summary": {"latest_on_hand": 12},
        "governance": {"advisory_only": True},
    }

    drivers = intelligence_context_drivers(context)

    assert "Forecast intelligence considered 2 registered signal(s)." in drivers
    assert "Forecast intelligence context confidence is 0.75." in drivers
    assert "Latest intelligence on-hand signal is 12 units." in drivers


def test_intelligence_context_builds_safe_warnings():
    context = {"signal_count": 0, "governance": {"advisory_only": False}}

    warnings = intelligence_context_warnings(context)

    assert "Intelligence context advisory marker is missing or false." in warnings
    assert "No registered intelligence signals were available for this forecast context." in warnings


def test_enrich_explanation_preserves_existing_summary_and_adds_context():
    explanation = ExplanationResult(
        summary="No reorder is suggested.",
        drivers=["Available stock is 12 units."],
        warnings=[],
    )
    context = {
        "signal_count": 1,
        "confidence": 0.8,
        "feature_summary": {},
        "governance": {"advisory_only": True},
    }

    enriched = enrich_explanation_with_intelligence_context(explanation, context)

    assert enriched.summary == explanation.summary
    assert "Available stock is 12 units." in enriched.drivers
    assert "Forecast intelligence considered 1 registered signal(s)." in enriched.drivers
    assert enriched.warnings == []


def test_empty_intelligence_context_does_not_change_explanation():
    explanation = ExplanationResult(summary="Stable forecast", drivers=["Base driver"], warnings=["Base warning"])

    enriched = enrich_explanation_with_intelligence_context(explanation, None)

    assert enriched == explanation
