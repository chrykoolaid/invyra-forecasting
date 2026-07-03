from __future__ import annotations

from dataclasses import dataclass, field

from invyra_forecasting.constants import Environment
from invyra_forecasting.signals.schema import ForecastSignal, ForecastSignalSource, ForecastSignalType
from invyra_forecasting.signals.validators import validate_forecast_signal


@dataclass
class InMemoryForecastSignalRegistry:
    """Local signal registry for Phase 2U development and tests.

    This registry stores normalized forecasting intelligence inputs only. It is
    intentionally read/write scoped to signals and does not touch inventory,
    stock movements, purchase orders, approvals, or ledger records.
    """

    _signals: list[ForecastSignal] = field(default_factory=list)

    def publish(self, signal: ForecastSignal) -> ForecastSignal:
        validate_forecast_signal(signal)
        self._signals.append(signal)
        return signal

    def publish_many(self, signals: list[ForecastSignal]) -> list[ForecastSignal]:
        accepted: list[ForecastSignal] = []
        for signal in signals:
            accepted.append(self.publish(signal))
        return accepted

    def list_signals(
        self,
        *,
        item_id: str | None = None,
        location_id: str | None = None,
        signal_type: ForecastSignalType | None = None,
        module_source: ForecastSignalSource | None = None,
        environment: Environment | None = None,
    ) -> list[ForecastSignal]:
        signals = self._signals
        if item_id is not None:
            signals = [signal for signal in signals if signal.item_id == item_id]
        if location_id is not None:
            signals = [signal for signal in signals if signal.location_id == location_id]
        if signal_type is not None:
            signals = [signal for signal in signals if signal.signal_type == signal_type]
        if module_source is not None:
            signals = [signal for signal in signals if signal.module_source == module_source]
        if environment is not None:
            signals = [signal for signal in signals if signal.environment == environment]
        return list(signals)

    def count(self) -> int:
        return len(self._signals)

    def clear(self) -> None:
        self._signals.clear()
