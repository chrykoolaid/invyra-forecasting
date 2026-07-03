from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from invyra_forecasting.constants import Environment


@dataclass(frozen=True)
class ForecastModelInput:
    """Stable model input generated from ForecastIntelligence.

    Models consume this contract instead of raw operational data. This keeps
    Inventory as the source of truth and preserves advisory-only forecasting.
    """

    item_id: str
    location_id: str
    environment: Environment
    analysis_window_days: int
    average_daily_demand: float
    latest_on_hand: float | None
    confidence: float
    evidence_refs: tuple[str, ...]
    feature_summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["environment"] = self.environment.value
        payload["evidence_refs"] = list(self.evidence_refs)
        return payload


@dataclass(frozen=True)
class ForecastModelOutput:
    """Advisory model output for item/location forecasting."""

    item_id: str
    location_id: str
    environment: Environment
    forecast_days: int
    forecast_quantity: float
    projected_days_of_cover: float | None
    stockout_risk: str
    confidence: float
    explanation: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    advisory_only: bool = True
    inventory_source_of_truth_preserved: bool = True
    model_name: str = "baseline_explainable_demand_model"
    model_version: str = "2W.1"

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["environment"] = self.environment.value
        payload["explanation"] = list(self.explanation)
        payload["evidence_refs"] = list(self.evidence_refs)
        return payload
