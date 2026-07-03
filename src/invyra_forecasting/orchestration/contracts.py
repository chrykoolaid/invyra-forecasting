from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from invyra_forecasting.constants import Environment


@dataclass(frozen=True)
class AdvisoryForecastRequest:
    """End-to-end advisory forecast request for one item/location.

    This request reads registered signals and produces a forecast output. It does
    not authorize any operational mutation or purchasing action.
    """

    item_id: str
    location_id: str
    environment: Environment = Environment.TRAINING
    analysis_window_days: int = 30
    forecast_days: int = 30


@dataclass(frozen=True)
class AdvisoryForecastResponse:
    """End-to-end advisory forecast response with intelligence and model traces."""

    item_id: str
    location_id: str
    environment: Environment
    analysis_window_days: int
    forecast_days: int
    forecast_quantity: float
    projected_days_of_cover: float | None
    stockout_risk: str
    confidence: float
    explanation: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    intelligence_summary: dict[str, Any] = field(default_factory=dict)
    model_metadata: dict[str, Any] = field(default_factory=dict)
    advisory_only: bool = True
    inventory_source_of_truth_preserved: bool = True

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["environment"] = self.environment.value
        payload["explanation"] = list(self.explanation)
        payload["evidence_refs"] = list(self.evidence_refs)
        return payload
