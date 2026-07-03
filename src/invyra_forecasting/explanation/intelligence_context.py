from __future__ import annotations

from typing import Any

from invyra_forecasting.schemas import ExplanationResult


def intelligence_context_drivers(intelligence_context: dict[str, Any] | None) -> list[str]:
    """Build explanation drivers from compact intelligence context metadata."""

    if not intelligence_context:
        return []

    drivers: list[str] = []
    signal_count = intelligence_context.get("signal_count")
    confidence = intelligence_context.get("confidence")
    if signal_count is not None:
        drivers.append(f"Forecast intelligence considered {signal_count} registered signal(s).")
    if confidence is not None:
        drivers.append(f"Forecast intelligence context confidence is {confidence}.")

    feature_summary = intelligence_context.get("feature_summary") or {}
    latest_on_hand = feature_summary.get("latest_on_hand")
    if latest_on_hand is not None:
        drivers.append(f"Latest intelligence on-hand signal is {latest_on_hand} units.")

    return drivers


def intelligence_context_warnings(intelligence_context: dict[str, Any] | None) -> list[str]:
    """Build explanation warnings from compact intelligence context metadata."""

    if not intelligence_context:
        return []

    warnings: list[str] = []
    governance = intelligence_context.get("governance") or {}
    if governance.get("advisory_only") is False:
        warnings.append("Intelligence context advisory marker is missing or false.")

    signal_count = intelligence_context.get("signal_count")
    if signal_count == 0:
        warnings.append("No registered intelligence signals were available for this forecast context.")

    return warnings


def enrich_explanation_with_intelligence_context(
    explanation: ExplanationResult,
    intelligence_context: dict[str, Any] | None,
) -> ExplanationResult:
    """Return an explanation enriched with intelligence metadata."""

    return ExplanationResult(
        summary=explanation.summary,
        drivers=explanation.drivers + intelligence_context_drivers(intelligence_context),
        warnings=explanation.warnings + intelligence_context_warnings(intelligence_context),
    )
