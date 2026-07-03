from __future__ import annotations

from dataclasses import dataclass

from invyra_forecasting.constants import Environment
from invyra_forecasting.signals.registry import InMemoryForecastSignalRegistry
from invyra_forecasting.signals.schema import ForecastSignal


@dataclass(frozen=True)
class SignalIngestionRequest:
    """Read-only request for signals from the registry."""

    item_id: str
    location_id: str
    environment: Environment
    analysis_window_days: int = 30


class ForecastSignalCollector:
    """Collect registered forecasting signals without touching source modules."""

    def __init__(self, registry: InMemoryForecastSignalRegistry) -> None:
        self._registry = registry

    def collect(self, request: SignalIngestionRequest) -> list[ForecastSignal]:
        """Return signals matching the item/location/environment boundary."""

        return self._registry.list_signals(
            item_id=request.item_id,
            location_id=request.location_id,
            environment=request.environment,
        )
