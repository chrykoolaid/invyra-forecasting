from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Callable

from invyra_forecasting.signals.schema import ForecastSignal


class FeatureCategory(StrEnum):
    """Enterprise feature categories used by the forecasting engine."""

    DEMAND = "DEMAND"
    INVENTORY = "INVENTORY"
    SUPPLY = "SUPPLY"
    TIME = "TIME"
    OPERATIONAL = "OPERATIONAL"
    PROMOTION = "PROMOTION"
    CONTEXT = "CONTEXT"


@dataclass(frozen=True)
class ForecastFeature:
    """Typed model-ready feature generated from advisory forecast signals.

    Forecast features are read-only intelligence objects. They do not mutate
    inventory, create stock movements, create purchase orders, approve purchase
    orders, or replace the inventory ledger as source of truth.
    """

    feature_id: str
    name: str
    category: FeatureCategory
    value: float | int | bool | str | None
    unit: str | None
    calculation_method: str
    source_signal_ids: tuple[str, ...] = ()
    data_window: str | None = None
    quality_score: float = 1.0
    confidence_score: float = 1.0
    generated_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    )
    version: str = "1.0"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0.0 <= self.quality_score <= 1.0:
            raise ValueError("quality_score must be between 0.0 and 1.0")
        if not 0.0 <= self.confidence_score <= 1.0:
            raise ValueError("confidence_score must be between 0.0 and 1.0")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["category"] = self.category.value
        payload["source_signal_ids"] = list(self.source_signal_ids)
        return payload


FeatureBuilder = Callable[[tuple[ForecastSignal, ...]], ForecastFeature]


@dataclass(frozen=True)
class FeatureDefinition:
    """Registry entry describing how a forecast feature is generated."""

    name: str
    category: FeatureCategory
    builder: FeatureBuilder
    version: str = "1.0"
    description: str | None = None
