from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from invyra_forecasting.constants import Environment
from invyra_forecasting.signals.schema import ForecastSignalDirection, ForecastSignalSource, ForecastSignalType


@dataclass(frozen=True)
class ForecastIntelligenceObject:
    """Evidence-backed signal interpretation consumed by forecast models.

    The object is advisory only. It preserves the source signal and evidence
    chain but never mutates inventory, ledger records, stock movements, or
    purchase orders.
    """

    intelligence_id: str
    source_signal_id: str
    signal_type: ForecastSignalType
    module_source: ForecastSignalSource
    item_id: str
    sku: str
    location_id: str
    timestamp_utc: str
    quantity: float
    unit: str
    direction: ForecastSignalDirection
    quality_score: float
    weight: float
    weighted_score: float
    features: dict[str, Any]
    evidence_chain: tuple[str, ...]
    confidence: float
    reason_code: str | None = None
    environment: Environment = Environment.TRAINING
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
