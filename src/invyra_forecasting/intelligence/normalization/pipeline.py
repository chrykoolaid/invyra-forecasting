from __future__ import annotations

from invyra_forecasting.signals.schema import ForecastSignal
from invyra_forecasting.signals.validators import validate_forecast_signal


class ForecastSignalNormalizationPipeline:
    """Validate and pass through already-normalized registry signals.

    Phase 2U owns signal normalization at publication time. Phase 2V re-checks
    the contract before intelligence processing so model inputs stay stable.
    """

    def normalize(self, signals: list[ForecastSignal]) -> list[ForecastSignal]:
        normalized: list[ForecastSignal] = []
        for signal in signals:
            validate_forecast_signal(signal)
            normalized.append(signal)
        return normalized
