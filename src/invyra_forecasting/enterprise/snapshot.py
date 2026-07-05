from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from invyra_forecasting.confidence import ConfidenceCalibrationService
from invyra_forecasting.evaluation import ForecastPrediction
from invyra_forecasting.intelligence.objects import ForecastIntelligence
from invyra_forecasting.intelligence.v2_builder import ForecastIntelligenceV2Builder
from invyra_forecasting.models import ForecastModelOrchestrator
from invyra_forecasting.registry import ModelRegistryEntry, ModelLifecycleState


@dataclass(frozen=True)
class EnterpriseForecastSnapshot:
    snapshot_id: str
    generated_at_utc: str
    item_id: str
    location_id: str
    orchestration_result: dict[str, Any]
    calibrated_confidence: dict[str, Any]
    evaluation_prediction: dict[str, Any]
    lifecycle_entry: dict[str, Any]
    intelligence_v2: dict[str, Any]
    advisory_only: bool = True
    read_only: bool = True
    inventory_source_of_truth_preserved: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.advisory_only:
            raise ValueError("enterprise snapshots must remain advisory-only")
        if not self.read_only:
            raise ValueError("enterprise snapshots must remain read-only")
        if not self.inventory_source_of_truth_preserved:
            raise ValueError("inventory source of truth must be preserved")

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "generated_at_utc": self.generated_at_utc,
            "item_id": self.item_id,
            "location_id": self.location_id,
            "orchestration_result": dict(self.orchestration_result),
            "calibrated_confidence": dict(self.calibrated_confidence),
            "evaluation_prediction": dict(self.evaluation_prediction),
            "lifecycle_entry": dict(self.lifecycle_entry),
            "intelligence_v2": dict(self.intelligence_v2),
            "advisory_only": self.advisory_only,
            "read_only": self.read_only,
            "inventory_source_of_truth_preserved": self.inventory_source_of_truth_preserved,
            "metadata": dict(self.metadata),
        }


class EnterpriseForecastSnapshotService:
    def __init__(
        self,
        *,
        orchestrator: ForecastModelOrchestrator | None = None,
        confidence_service: ConfidenceCalibrationService | None = None,
        intelligence_v2_builder: ForecastIntelligenceV2Builder | None = None,
    ) -> None:
        self._orchestrator = orchestrator or ForecastModelOrchestrator()
        self._confidence_service = confidence_service or ConfidenceCalibrationService()
        self._intelligence_v2_builder = intelligence_v2_builder or ForecastIntelligenceV2Builder()

    def build(
        self,
        intelligence: ForecastIntelligence,
        *,
        forecast_days: int = 30,
        forecast_type: str = "item_location_demand",
    ) -> EnterpriseForecastSnapshot:
        orchestration = self._orchestrator.forecast(intelligence, forecast_type=forecast_type, forecast_days=forecast_days)
        calibrated = self._confidence_service.calibrate(intelligence, orchestration)
        prediction = self._prediction(orchestration)
        lifecycle = self._lifecycle(orchestration, forecast_type, forecast_days)
        intelligence_v2 = self._intelligence_v2_builder.from_v1(intelligence, forecast_horizon_days=forecast_days)
        return EnterpriseForecastSnapshot(
            snapshot_id=str(uuid4()),
            generated_at_utc=datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
            item_id=intelligence.item_id,
            location_id=intelligence.location_id,
            orchestration_result=orchestration.to_dict(),
            calibrated_confidence=calibrated.to_dict(),
            evaluation_prediction=prediction.to_dict(),
            lifecycle_entry=lifecycle.to_dict(),
            intelligence_v2=intelligence_v2.to_dict(),
            advisory_only=orchestration.advisory_only and calibrated.advisory_only,
            read_only=True,
            inventory_source_of_truth_preserved=(
                orchestration.inventory_source_of_truth_preserved and calibrated.inventory_source_of_truth_preserved
            ),
            metadata={"phase": "5I", "forecast_type": forecast_type, "forecast_days": forecast_days, "evaluation_ready": True},
        )

    def _prediction(self, orchestration) -> ForecastPrediction:
        output = orchestration.model_output
        return ForecastPrediction(
            forecast_id=str(uuid4()),
            item_id=output.item_id,
            location_id=output.location_id,
            model_name=output.model_name,
            model_version=output.model_version,
            forecast_horizon_days=output.forecast_days,
            predicted_quantity=output.forecast_quantity,
            confidence=output.confidence,
            metadata={"stockout_risk": output.stockout_risk},
        )

    def _lifecycle(self, orchestration, forecast_type: str, forecast_days: int) -> ModelRegistryEntry:
        selected = orchestration.selection.selected_model
        return ModelRegistryEntry(
            model_id=f"{selected.model_name}::{selected.model_version}",
            model_name=selected.model_name,
            model_version=selected.model_version,
            forecast_type=forecast_type,
            lifecycle_state=ModelLifecycleState.PRODUCTION,
            supported_horizons_days=(forecast_days,),
            owner="Invyra Forecasting Engine",
            strengths=tuple(selected.strengths),
            limitations=tuple(selected.limitations),
        )
