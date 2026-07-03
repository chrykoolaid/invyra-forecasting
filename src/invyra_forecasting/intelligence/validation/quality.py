from __future__ import annotations

from datetime import UTC, datetime

from invyra_forecasting.intelligence.objects import SignalQualityAssessment
from invyra_forecasting.signals.schema import ForecastSignal


def _parse_timestamp_utc(timestamp_utc: str) -> datetime | None:
    try:
        return datetime.fromisoformat(timestamp_utc.replace("Z", "+00:00"))
    except ValueError:
        return None


class SignalQualityAssessor:
    """Scores signal quality before advisory forecasting use."""

    def assess(self, signal: ForecastSignal, *, analysis_window_days: int = 30) -> SignalQualityAssessment:
        issues: list[str] = []

        timestamp = _parse_timestamp_utc(signal.timestamp_utc)
        if timestamp is None:
            freshness_score = 0.0
            issues.append("invalid_timestamp")
        else:
            age_days = max((datetime.now(UTC) - timestamp).days, 0)
            freshness_score = max(0.0, 1.0 - (age_days / max(analysis_window_days, 1)))
            if age_days > analysis_window_days:
                issues.append("outside_analysis_window")

        required_values = [signal.signal_id, signal.item_id, signal.sku, signal.location_id, signal.unit, signal.timestamp_utc]
        completeness_score = sum(1 for value in required_values if bool(str(value).strip())) / len(required_values)
        if completeness_score < 1.0:
            issues.append("incomplete_required_fields")

        reliability_score = signal.confidence
        if signal.evidence_ref is None:
            reliability_score = min(reliability_score, 0.7)
            issues.append("missing_evidence_ref")

        score = round((freshness_score + completeness_score + reliability_score) / 3, 4)
        return SignalQualityAssessment(
            signal_id=signal.signal_id,
            score=score,
            freshness_score=round(freshness_score, 4),
            completeness_score=round(completeness_score, 4),
            reliability_score=round(reliability_score, 4),
            issues=tuple(issues),
        )

    def assess_many(self, signals: list[ForecastSignal], *, analysis_window_days: int = 30) -> list[SignalQualityAssessment]:
        return [self.assess(signal, analysis_window_days=analysis_window_days) for signal in signals]
