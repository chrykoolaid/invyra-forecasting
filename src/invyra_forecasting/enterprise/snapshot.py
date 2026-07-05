from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from invyra_forecasting.confidence import CalibratedConfidence, ConfidenceCalibrationService
from invyra_forecasting.evidence import EvidenceRankingResult, EvidenceRankingService, RankedEvidenceItem
from invyra_forecasting.evaluation import ForecastPrediction
from invyra_forecasting.intelligence.objects import ForecastIntelligence
from invyra_forecasting.intelligence.v2_builder import ForecastIntelligenceV2Builder
from invyra_forecasting.models import ForecastModelOrchestrator, OrchestratedForecastResult
from invyra_forecasting.registry import ModelLifecycleRegistry, ModelRegistryEntry, ModelLifecycleState


@dataclass(frozen=True)
class EnterpriseForecastSnapshot:
    snapshot_id: str
    generated_at_utc: str
    item_id: str
    location_id: str
    orchestration_result: OrchestratedForecastResult
    calibrated_confidence: CalibratedConfidence
    evidence_ranking: EvidenceRankingResult
    evaluation_prediction: ForecastPrediction
    lifecycle_entry: ModelRegistryEntry
    intelligence_v2: dict[str, Any]
    advisory_only: bool = True
    read_only: bool = True
    inventory_source_of_truth_preserved: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.advisory_only:
            raise ValueError("enterprise forecast snapshots must remain advisory-only")
        if not self.read_only:
            raise ValueError("enterprise forecast snapshots must remain read-only")
        if not self.inventory_source_of_truth_preserved:
            raise ValueError("inventory source of truth must be preserved")

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "generated_at_utc": self.generated_at_utc,
            "item_id": self.item_id,
            "location_id": self.location_id,
            "orchestration_result": self.orchestration_result.to_dict(),
            "calibrated_confidence": self.calibrated_confidence.to_dict(),
            "evidence_ranking": self.evidence_ranking.to_dict(),
            "evaluation_prediction": self.evaluation_prediction.to_dict(),
            "lifecycle_entry": self.lifecycle_entry.to_dict(),
            "intelligence_v2": dict(self.intelligence_v2),
            "advisory_only": self.advisory_only,
            "read_only": self.read_only,
            "inventory_source_of_truth_preserved": self.inventory_source_of_truth_preserved,
            "metadata": dict(self.metadata),
        }


class EnterpriseForecastSnapshotService:
    """Builds an end-to-end read-only enterprise forecast snapshot."""

    def __init__(
        self,
        *,
        orchestrator: ForecastModelOrchestrator | None = None,
        confidence_service: ConfidenceCalibrationService | None = None,
        evidence_service: EvidenceRankingService | None = None,
        intelligence_v2_builder: ForecastIntelligenceV2Builder | None = None,
        lifecycle_registry: ModelLifecycleRegistry | None = None,
    ) -> None:
        self._orchestrator = orchestrator or ForecastModelOrchestrator()
        self._confidence_service = confidence_service or ConfidenceCalibrationService()
        self._evidence_service = evidence_service or EvidenceRankingService()
        self._intelligence_v2_builder = intelligence_v2_builder or ForecastIntelligenceV2Builder()
        self._lifecycle_registry = lifecycle_registry or ModelLifecycleRegistry()

    def build(
        self,
        intelligence: ForecastIntelligence,
        *,
        forecast_days: int = 30,
        forecast_type: str = "item_location_demand",
    ) -> EnterpriseForecastSnapshot:
        orchestration = self._orchestrator.forecast(
            intelligence,
            forecast_type=forecast_type,
            forecast_days=forecast_days,
        )
        calibrated = self._confidence_service.calibrate(intelligence, orchestration)
        evidence = self._rank_evidence(intelligence, orchestration, calibrated)
        prediction = self._prediction_from_orchestration(orchestration)
        lifecycle_entry = self._lifecycle_entry(orchestration, forecast_type, forecast_days)
        intelligence_v2 = self._intelligence_v2_builder.from_v1(
            intelligence,
            forecast_horizon_days=forecast_days,
        ).to_dict()
        return EnterpriseForecastSnapshot(
            snapshot_id=str(uuid4()),
            generated_at_utc=datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
            item_id=intelligence.item_id,
            location_id=intelligence.location_id,
            orchestration_result=orchestration,
            calibrated_confidence=calibrated,
            evidence_ranking=evidence,
            evaluation_prediction=prediction,
            lifecycle_entry=lifecycle_entry,
            intelligence_v2=intelligence_v2,
            advisory_only=orchestration.advisory_only and calibrated.advisory_only,
            read_only=True,
            inventory_source_of_truth_preserved=(
                orchestration.inventory_source_of_truth_preserved
                and calibrated.inventory_source_of_truth_preserved
                and evidence.inventory_source_of_truth_preserved
            ),
            metadata={
                "phase": "5I",
                "forecast_type": forecast_type,
                "forecast_days": forecast_days,
                "evaluation_ready": True,
            },
        )

    def _rank_evidence(
        self,
        intelligence: ForecastIntelligence,
        orchestration: OrchestratedForecastResult,
        calibrated: CalibratedConfidence,
    ) -> EvidenceRankingResult:
        items: list[RankedEvidenceItem] = []
        score = calibrated.overall_confidence
        for index, link in enumerate(intelligence.evidence_links, start=1):
            items.append(
                RankedEvidenceItem(
                    rank=index,
                    signal_id=link.signal_id,
                    evidence_ref=link.evidence_ref,
                    module_source=link.module_source,
                    signal_type=link.signal_type,
                    relevance_score=score,
                    reliability_score=score,
                    completeness_score=score,
                    business_impact_score=score,
                    confidence_contribution=score,
                    overall_score=score,
                    impact="HIGH" if score >= 0.75 else "MODERATE",
                    direction="supporting",
                    explanation="Evidence linked to enterprise forecast snapshot.",
                    metadata={"phase": "5I"},
                )
            )
        return self._evidence_service.rank(tuple(items))

    def _prediction_from_orchestration(self, orchestration: OrchestratedForecastResult) -> ForecastPrediction:
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

    def _lifecycle_entry(
        self,
        orchestration: OrchestratedForecastResult,
        forecast_type: str,
        forecast_days: int,
    ) -> ModelRegistryEntry:
        selected = orchestration.selection.selected_model
        model_id = f"{selected.model_name}::{selected.model_version}"
        try:
            return self._lifecycle_registry.get(model_id)
        except KeyError:
            entry = ModelRegistryEntry(
                model_id=model_id,
                model_name=selected.model_name,
                model_version=selected.model_version,
                forecast_type=forecast_type,
                lifecycle_state=ModelLifecycleState.PRODUCTION,
                supported_horizons_days=(forecast_days,),
                owner="Invyra Forecasting Engine",
                description="Runtime-selected model captured by Phase 5I enterprise snapshot.",
                strengths=tuple(selected.strengths),
                limitations=tuple(selected.limitations),
            )
            self._lifecycle_registry.register(entry)
            return entry
