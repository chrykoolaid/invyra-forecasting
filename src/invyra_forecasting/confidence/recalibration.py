from __future__ import annotations

from typing import Any

from invyra_forecasting.schemas import ConfidenceResult


def _rating(score: float) -> str:
    if score >= 75:
        return "High"
    if score >= 45:
        return "Medium"
    return "Low"


def _score_from_record(record: dict[str, Any]) -> float | None:
    try:
        return float(record.get("accuracy_score"))
    except (TypeError, ValueError):
        return None


def recalibrate_confidence_with_accuracy(confidence: ConfidenceResult, accuracy_history: list[dict[str, Any]], window: int = 10) -> ConfidenceResult:
    """Adjust confidence using recent forecast accuracy records.

    No history means no change. This keeps Phase 1F advisory and safe while
    adding the first feedback loop between forecast quality and confidence.
    """

    if not accuracy_history:
        return confidence

    effective_window = max(1, window)
    records = accuracy_history[-effective_window:]
    scores = [score for record in records if (score := _score_from_record(record)) is not None]
    if not scores:
        return confidence

    average_accuracy = sum(scores) / len(scores)
    adjusted_score = confidence.score
    reasons = list(confidence.reasons)
    reasons.append(f"Accuracy recalibration used {len(scores)} historical evaluation(s); average accuracy score {average_accuracy:.2f}.")

    if average_accuracy >= 85:
        adjusted_score += 5
        reasons.append("Strong historical forecast accuracy increased confidence slightly.")
    elif average_accuracy < 65:
        adjusted_score -= 15
        reasons.append("Weak historical forecast accuracy reduced confidence.")
    else:
        reasons.append("Mixed historical forecast accuracy caused no major confidence adjustment.")

    recent_scores = scores[-3:]
    if len(recent_scores) == 3 and all(score < 65 for score in recent_scores):
        adjusted_score -= 10
        reasons.append("Three recent low-accuracy evaluations reduced confidence further.")

    biases = [str(record.get("bias", "")) for record in records]
    directional_biases = [bias for bias in biases if bias in {"Over Forecast", "Under Forecast"}]
    if len(directional_biases) >= 3:
        over_count = directional_biases.count("Over Forecast")
        under_count = directional_biases.count("Under Forecast")
        dominant_count = max(over_count, under_count)
        dominant_bias = "Over Forecast" if over_count >= under_count else "Under Forecast"
        if dominant_count / len(directional_biases) >= 0.7:
            adjusted_score -= 5
            reasons.append(f"Repeated {dominant_bias.lower()} bias reduced confidence.")

    adjusted_score = max(0.0, min(100.0, adjusted_score))
    return ConfidenceResult(rating=_rating(adjusted_score), score=round(adjusted_score, 2), reasons=reasons)
