from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from invyra_forecasting.constants import Environment
from invyra_forecasting.features.feature_contracts import ForecastFeature
from invyra_forecasting.intelligence.objects import EvidenceLink, ForecastIntelligence, SignalQualityAssessment
from invyra_forecasting.signals.schema import ForecastSignal


@dataclass(frozen=True)
class ForecastIdentity:
    """Identity of the forecast case being evaluated."""

    item_id: str
    location_id: str
    environment: Environment
    forecast_type: str = "item_location_demand"
    forecast_horizon_days: int | None = None
    request_id: str = field(default_factory=lambda: str(uuid4()))
    request_timestamp_utc: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["environment"] = self.environment.value
        return payload


@dataclass(frozen=True)
class ForecastContextPackage:
    """Operational context carried with a forecast case.

    Context is advisory metadata only. It does not own inventory, purchase order,
    supplier, markdown, wastage, stocktake, transfer, or POS truth.
    """

    current_inventory: dict[str, Any] = field(default_factory=dict)
    outstanding_purchase_orders: tuple[dict[str, Any], ...] = ()
    supplier_status: dict[str, Any] = field(default_factory=dict)
    recent_sales: tuple[dict[str, Any], ...] = ()
    recent_transfers: tuple[dict[str, Any], ...] = ()
    recent_stocktakes: tuple[dict[str, Any], ...] = ()
    open_markdown_events: tuple[dict[str, Any], ...] = ()
    waste_activity: tuple[dict[str, Any], ...] = ()
    operational_alerts: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ConfidencePackage:
    """Dimension-level confidence context for forecast explainability."""

    overall_confidence: float
    data_confidence: float
    feature_confidence: float
    evidence_confidence: float
    model_confidence: float | None = None
    context_confidence: float | None = None
    stability_confidence: float | None = None
    confidence_reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        values = (
            self.overall_confidence,
            self.data_confidence,
            self.feature_confidence,
            self.evidence_confidence,
            *(value for value in (self.model_confidence, self.context_confidence, self.stability_confidence) if value is not None),
        )
        for value in values:
            if not 0.0 <= value <= 1.0:
                raise ValueError("confidence values must be between 0.0 and 1.0")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["confidence_reasons"] = list(self.confidence_reasons)
        return payload


@dataclass(frozen=True)
class QualityAssessmentPackage:
    """Pre-model quality checks for a forecast case."""

    quality_score: float
    missing_data: tuple[str, ...] = ()
    outliers: tuple[str, ...] = ()
    incomplete_history: bool = False
    sparse_sales: bool = False
    lead_time_quality: str | None = None
    supplier_consistency: str | None = None
    inventory_integrity: str | None = None
    signal_completeness: str | None = None

    def __post_init__(self) -> None:
        if not 0.0 <= self.quality_score <= 1.0:
            raise ValueError("quality_score must be between 0.0 and 1.0")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["missing_data"] = list(self.missing_data)
        payload["outliers"] = list(self.outliers)
        return payload


@dataclass(frozen=True)
class ForecastConstraints:
    """Governance constraints that travel with every forecast case."""

    advisory_only: bool = True
    inventory_source_of_truth_preserved: bool = True
    may_modify_inventory: bool = False
    may_create_stock_movements: bool = False
    may_create_purchase_orders: bool = False
    may_approve_purchase_orders: bool = False
    may_override_ledger_truth: bool = False
    forecast_horizon_limit_days: int | None = None
    notes: tuple[str, ...] = ()

    def assert_guardrails(self) -> None:
        if not self.advisory_only:
            raise ValueError("forecast constraints must remain advisory-only")
        if not self.inventory_source_of_truth_preserved:
            raise ValueError("inventory source of truth must be preserved")
        prohibited = (
            self.may_modify_inventory,
            self.may_create_stock_movements,
            self.may_create_purchase_orders,
            self.may_approve_purchase_orders,
            self.may_override_ledger_truth,
        )
        if any(prohibited):
            raise ValueError("forecast constraints cannot allow operational mutation")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["notes"] = list(self.notes)
        return payload


@dataclass(frozen=True)
class GovernanceMetadata:
    """Version metadata for reproducible forecast case generation."""

    pipeline_version: str = "2V"
    feature_version: str = "5A"
    registry_version: str = "5A"
    engine_version: str = "0.1.0"
    configuration_version: str | None = None
    processing_time_ms: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AuditMetadata:
    """Audit metadata for a forecast case."""

    request_id: str
    generated_timestamp_utc: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    )
    evidence_snapshot_id: str | None = None
    feature_set_version: str = "5A"
    pipeline_hash: str | None = None
    processing_duration_ms: float | None = None
    audit_refs: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["audit_refs"] = list(self.audit_refs)
        return payload


@dataclass(frozen=True)
class ForecastIntelligenceV2:
    """Enterprise forecast case contract.

    This V2 object packages identity, context, engineered features, evidence,
    confidence, quality, governance, and audit metadata. It is model-agnostic,
    advisory-only, and does not replace the existing ForecastIntelligence object.
    """

    identity: ForecastIdentity
    context: ForecastContextPackage
    engineered_features: tuple[ForecastFeature, ...]
    evidence_package: tuple[EvidenceLink, ...]
    confidence_package: ConfidencePackage
    quality_assessment: QualityAssessmentPackage
    forecast_constraints: ForecastConstraints
    governance_metadata: GovernanceMetadata
    audit_metadata: AuditMetadata
    normalized_signals: tuple[ForecastSignal, ...] = ()
    quality_assessments: tuple[SignalQualityAssessment, ...] = ()
    created_from_version: str = "ForecastIntelligenceV1"

    def __post_init__(self) -> None:
        self.forecast_constraints.assert_guardrails()

    def to_dict(self) -> dict[str, Any]:
        return {
            "identity": self.identity.to_dict(),
            "context": self.context.to_dict(),
            "engineered_features": [feature.to_dict() for feature in self.engineered_features],
            "evidence_package": [evidence.to_dict() for evidence in self.evidence_package],
            "confidence_package": self.confidence_package.to_dict(),
            "quality_assessment": self.quality_assessment.to_dict(),
            "forecast_constraints": self.forecast_constraints.to_dict(),
            "governance_metadata": self.governance_metadata.to_dict(),
            "audit_metadata": self.audit_metadata.to_dict(),
            "normalized_signals": [signal.to_dict() for signal in self.normalized_signals],
            "quality_assessments": [assessment.to_dict() for assessment in self.quality_assessments],
            "created_from_version": self.created_from_version,
        }

    @classmethod
    def from_v1(
        cls,
        intelligence: ForecastIntelligence,
        *,
        engineered_features: tuple[ForecastFeature, ...] = (),
        forecast_horizon_days: int | None = None,
    ) -> "ForecastIntelligenceV2":
        request_id = str(uuid4())
        feature_confidence = (
            sum(feature.confidence_score for feature in engineered_features) / len(engineered_features)
            if engineered_features
            else intelligence.confidence
        )
        evidence_confidence = 1.0 if intelligence.evidence_links else 0.5
        missing_data = () if intelligence.normalized_signals else ("normalized_signals",)
        return cls(
            identity=ForecastIdentity(
                item_id=intelligence.item_id,
                location_id=intelligence.location_id,
                environment=intelligence.environment,
                forecast_horizon_days=forecast_horizon_days,
                request_id=request_id,
            ),
            context=ForecastContextPackage(
                current_inventory={"latest_on_hand": intelligence.features.latest_on_hand},
                operational_alerts=tuple(intelligence.processing_metadata.get("operational_alerts", ())),
            ),
            engineered_features=engineered_features,
            evidence_package=intelligence.evidence_links,
            confidence_package=ConfidencePackage(
                overall_confidence=intelligence.confidence,
                data_confidence=intelligence.confidence,
                feature_confidence=round(feature_confidence, 4),
                evidence_confidence=evidence_confidence,
                confidence_reasons=("Derived from Phase 2V signal quality and Phase 5A engineered feature confidence.",),
            ),
            quality_assessment=QualityAssessmentPackage(
                quality_score=intelligence.confidence,
                missing_data=missing_data,
                signal_completeness="available" if intelligence.normalized_signals else "missing",
            ),
            forecast_constraints=ForecastConstraints(),
            governance_metadata=GovernanceMetadata(
                processing_time_ms=intelligence.processing_metadata.get("processing_time_ms"),
            ),
            audit_metadata=AuditMetadata(
                request_id=request_id,
                evidence_snapshot_id=intelligence.processing_metadata.get("evidence_snapshot_id"),
                audit_refs=intelligence.audit_refs,
            ),
            normalized_signals=intelligence.normalized_signals,
            quality_assessments=intelligence.quality_assessments,
        )
