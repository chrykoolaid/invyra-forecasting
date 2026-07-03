from __future__ import annotations

from dataclasses import dataclass

from invyra_forecasting.constants import Environment
from invyra_forecasting.intelligence.evidence.linker import EvidenceLinker
from invyra_forecasting.intelligence.features.extractor import ForecastFeatureExtractor
from invyra_forecasting.intelligence.ingestion.collector import ForecastSignalCollector, SignalIngestionRequest
from invyra_forecasting.intelligence.normalization.pipeline import ForecastSignalNormalizationPipeline
from invyra_forecasting.intelligence.objects import ForecastIntelligence
from invyra_forecasting.intelligence.validation.quality import SignalQualityAssessor
from invyra_forecasting.intelligence.weighting.scorer import SignalWeightScorer
from invyra_forecasting.signals.registry import InMemoryForecastSignalRegistry


@dataclass(frozen=True)
class ForecastIntelligenceRequest:
    """Request to build model-ready intelligence for one item/location."""

    item_id: str
    location_id: str
    environment: Environment = Environment.TRAINING
    analysis_window_days: int = 30


class ForecastIntelligencePipeline:
    """Enterprise intelligence pipeline between signals and forecast models."""

    def __init__(
        self,
        registry: InMemoryForecastSignalRegistry,
        *,
        collector: ForecastSignalCollector | None = None,
        normalizer: ForecastSignalNormalizationPipeline | None = None,
        quality_assessor: SignalQualityAssessor | None = None,
        weight_scorer: SignalWeightScorer | None = None,
        feature_extractor: ForecastFeatureExtractor | None = None,
        evidence_linker: EvidenceLinker | None = None,
    ) -> None:
        self._collector = collector or ForecastSignalCollector(registry)
        self._normalizer = normalizer or ForecastSignalNormalizationPipeline()
        self._quality_assessor = quality_assessor or SignalQualityAssessor()
        self._weight_scorer = weight_scorer or SignalWeightScorer()
        self._feature_extractor = feature_extractor or ForecastFeatureExtractor()
        self._evidence_linker = evidence_linker or EvidenceLinker()

    def build(self, request: ForecastIntelligenceRequest) -> ForecastIntelligence:
        ingestion_request = SignalIngestionRequest(
            item_id=request.item_id,
            location_id=request.location_id,
            environment=request.environment,
            analysis_window_days=request.analysis_window_days,
        )
        ingested_signals = self._collector.collect(ingestion_request)
        normalized_signals = self._normalizer.normalize(ingested_signals)
        quality_assessments = self._quality_assessor.assess_many(
            normalized_signals,
            analysis_window_days=request.analysis_window_days,
        )
        weighted_signals = self._weight_scorer.score_many(normalized_signals, quality_assessments)
        features = self._feature_extractor.extract(
            weighted_signals,
            item_id=request.item_id,
            location_id=request.location_id,
            analysis_window_days=request.analysis_window_days,
        )
        evidence_links = self._evidence_linker.link(normalized_signals)
        confidence = self._calculate_confidence(weighted_signals)

        return ForecastIntelligence(
            item_id=request.item_id,
            location_id=request.location_id,
            environment=request.environment,
            analysis_window_days=request.analysis_window_days,
            normalized_signals=tuple(normalized_signals),
            quality_assessments=tuple(quality_assessments),
            weighted_signals=tuple(weighted_signals),
            features=features,
            evidence_links=tuple(evidence_links),
            confidence=confidence,
            processing_metadata={
                "pipeline_phase": "2V",
                "signal_count": len(normalized_signals),
                "advisory_only": True,
                "inventory_source_of_truth_preserved": True,
            },
            audit_refs=tuple(link.evidence_ref for link in evidence_links),
        )

    def _calculate_confidence(self, weighted_signals: list) -> float:
        if not weighted_signals:
            return 0.0
        average_weight = sum(weighted.weight for weighted in weighted_signals) / len(weighted_signals)
        return round(max(0.0, min(1.0, average_weight)), 4)
