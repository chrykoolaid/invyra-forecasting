from __future__ import annotations

from dataclasses import dataclass, field

from invyra_forecasting.signals.schema import ForecastSignal
from invyra_forecasting.signals.validators import validate_forecast_signal


@dataclass(frozen=True)
class SignalQualityAssessment:
    """Quality score for a validated forecasting signal."""

    score: float
    reasons: tuple[str, ...] = field(default_factory=tuple)


def assess_signal_quality(signal: ForecastSignal) -> SignalQualityAssessment:
    """Score a signal without changing the source operational record."""

    validate_forecast_signal(signal)

    score = signal.confidence
    reasons: list[str] = [f"source confidence {signal.confidence:.2f}"]

    if signal.evidence_ref:
        reasons.append("evidence reference present")
    else:
        score -= 0.15
        reasons.append("missing evidence reference")

    if signal.reason_code:
        reasons.append("reason code present")
    else:
        score -= 0.05
        reasons.append("missing reason code")

    if signal.metadata:
        reasons.append("metadata present")
    else:
        score -= 0.05
        reasons.append("missing metadata")

    return SignalQualityAssessment(score=max(0.0, min(1.0, score)), reasons=tuple(reasons))
