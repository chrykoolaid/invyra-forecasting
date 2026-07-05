from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Iterable

from invyra_forecasting.models.orchestration import ModelLifecycleStatus


class ModelGovernanceEventType(StrEnum):
    REGISTERED = "REGISTERED"
    ACTIVATED = "ACTIVATED"
    RETIRED = "RETIRED"
    METADATA_UPDATED = "METADATA_UPDATED"


@dataclass(frozen=True)
class ModelCompatibilityProfile:
    forecast_types: tuple[str, ...] = ("item_location_demand",)
    horizons_days: tuple[int, ...] = (7, 14, 30, 60, 90)
    signal_types: tuple[str, ...] = ()
    min_engine_version: str | None = None
    max_engine_version: str | None = None

    def __post_init__(self) -> None:
        if not self.forecast_types:
            raise ValueError("forecast_types must not be empty")
        if not self.horizons_days:
            raise ValueError("horizons_days must not be empty")
        if any(day < 1 for day in self.horizons_days):
            raise ValueError("horizons_days must contain positive values")

    def supports(self, *, forecast_type: str, forecast_days: int) -> bool:
        return forecast_type in self.forecast_types and forecast_days in self.horizons_days

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["forecast_types"] = list(self.forecast_types)
        payload["horizons_days"] = list(self.horizons_days)
        payload["signal_types"] = list(self.signal_types)
        return payload


@dataclass(frozen=True)
class ModelRegistryEntryV2:
    model_id: str
    model_name: str
    model_version: str
    status: ModelLifecycleStatus = ModelLifecycleStatus.TESTING
    compatibility: ModelCompatibilityProfile = field(default_factory=ModelCompatibilityProfile)
    created_at_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    activated_at_utc: str | None = None
    retired_at_utc: str | None = None
    replaces_model_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    advisory_only: bool = True
    inventory_source_of_truth_preserved: bool = True

    def __post_init__(self) -> None:
        if not self.model_id:
            raise ValueError("model_id is required")
        if not self.model_name:
            raise ValueError("model_name is required")
        if not self.model_version:
            raise ValueError("model_version is required")
        if not self.advisory_only:
            raise ValueError("model registry entries must remain advisory-only")
        if not self.inventory_source_of_truth_preserved:
            raise ValueError("inventory source of truth must be preserved")
        if self.status == ModelLifecycleStatus.RETIRED and self.retired_at_utc is None:
            raise ValueError("retired models must include retired_at_utc")
        if self.status == ModelLifecycleStatus.PRODUCTION and self.activated_at_utc is None:
            raise ValueError("production models must include activated_at_utc")

    @property
    def family_key(self) -> str:
        return self.model_name

    def supports(self, *, forecast_type: str, forecast_days: int) -> bool:
        return self.compatibility.supports(forecast_type=forecast_type, forecast_days=forecast_days)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["status"] = self.status.value
        payload["compatibility"] = self.compatibility.to_dict()
        return payload


@dataclass(frozen=True)
class ModelGovernanceEvent:
    event_id: str
    model_id: str
    event_type: ModelGovernanceEventType
    created_at_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    previous_status: ModelLifecycleStatus | None = None
    new_status: ModelLifecycleStatus | None = None
    reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    advisory_only: bool = True

    def __post_init__(self) -> None:
        if not self.event_id:
            raise ValueError("event_id is required")
        if not self.model_id:
            raise ValueError("model_id is required")
        if not self.advisory_only:
            raise ValueError("model governance events must remain advisory-only")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["event_type"] = self.event_type.value
        payload["previous_status"] = self.previous_status.value if self.previous_status else None
        payload["new_status"] = self.new_status.value if self.new_status else None
        return payload


class ModelRegistryV2:
    def __init__(self, entries: Iterable[ModelRegistryEntryV2] = ()) -> None:
        self._entries: dict[str, ModelRegistryEntryV2] = {}
        self._events: list[ModelGovernanceEvent] = []
        for entry in entries:
            self.register(entry)

    def register(self, entry: ModelRegistryEntryV2, *, reason: str | None = None) -> ModelRegistryEntryV2:
        if entry.model_id in self._entries:
            raise ValueError(f"model already registered: {entry.model_id}")
        self._entries[entry.model_id] = entry
        self._record_event(entry.model_id, ModelGovernanceEventType.REGISTERED, None, entry.status, reason)
        return entry

    def get(self, model_id: str) -> ModelRegistryEntryV2 | None:
        return self._entries.get(model_id)

    def all(self) -> tuple[ModelRegistryEntryV2, ...]:
        return tuple(sorted(self._entries.values(), key=lambda entry: (entry.model_name, entry.model_version, entry.model_id)))

    def active(self) -> tuple[ModelRegistryEntryV2, ...]:
        return tuple(entry for entry in self.all() if entry.status == ModelLifecycleStatus.PRODUCTION)

    def version_history(self, model_name: str) -> tuple[ModelRegistryEntryV2, ...]:
        return tuple(entry for entry in self.all() if entry.model_name == model_name)

    def compatible(self, *, forecast_type: str, forecast_days: int) -> tuple[ModelRegistryEntryV2, ...]:
        return tuple(
            entry
            for entry in self.all()
            if entry.status in {ModelLifecycleStatus.APPROVED, ModelLifecycleStatus.PRODUCTION}
            and entry.supports(forecast_type=forecast_type, forecast_days=forecast_days)
        )

    def activate(self, model_id: str, *, reason: str | None = None) -> ModelRegistryEntryV2:
        entry = self._require_entry(model_id)
        if entry.status == ModelLifecycleStatus.RETIRED:
            raise ValueError("retired models cannot be activated")
        updated = ModelRegistryEntryV2(
            model_id=entry.model_id,
            model_name=entry.model_name,
            model_version=entry.model_version,
            status=ModelLifecycleStatus.PRODUCTION,
            compatibility=entry.compatibility,
            created_at_utc=entry.created_at_utc,
            activated_at_utc=datetime.now(timezone.utc).isoformat(),
            retired_at_utc=entry.retired_at_utc,
            replaces_model_id=entry.replaces_model_id,
            metadata=dict(entry.metadata),
        )
        self._entries[model_id] = updated
        self._record_event(model_id, ModelGovernanceEventType.ACTIVATED, entry.status, updated.status, reason)
        return updated

    def retire(self, model_id: str, *, reason: str | None = None) -> ModelRegistryEntryV2:
        entry = self._require_entry(model_id)
        if entry.status == ModelLifecycleStatus.RETIRED:
            return entry
        updated = ModelRegistryEntryV2(
            model_id=entry.model_id,
            model_name=entry.model_name,
            model_version=entry.model_version,
            status=ModelLifecycleStatus.RETIRED,
            compatibility=entry.compatibility,
            created_at_utc=entry.created_at_utc,
            activated_at_utc=entry.activated_at_utc,
            retired_at_utc=datetime.now(timezone.utc).isoformat(),
            replaces_model_id=entry.replaces_model_id,
            metadata=dict(entry.metadata),
        )
        self._entries[model_id] = updated
        self._record_event(model_id, ModelGovernanceEventType.RETIRED, entry.status, updated.status, reason)
        return updated

    def events(self, model_id: str | None = None) -> tuple[ModelGovernanceEvent, ...]:
        if model_id is None:
            return tuple(self._events)
        return tuple(event for event in self._events if event.model_id == model_id)

    def validate(self) -> tuple[str, ...]:
        issues: list[str] = []
        for entry in self.all():
            if entry.replaces_model_id and entry.replaces_model_id not in self._entries:
                issues.append(f"{entry.model_id} replaces missing model {entry.replaces_model_id}")
            if entry.status == ModelLifecycleStatus.PRODUCTION and not entry.activated_at_utc:
                issues.append(f"{entry.model_id} is production without activated_at_utc")
        return tuple(issues)

    def _require_entry(self, model_id: str) -> ModelRegistryEntryV2:
        entry = self.get(model_id)
        if entry is None:
            raise ValueError(f"model is not registered: {model_id}")
        return entry

    def _record_event(
        self,
        model_id: str,
        event_type: ModelGovernanceEventType,
        previous_status: ModelLifecycleStatus | None,
        new_status: ModelLifecycleStatus | None,
        reason: str | None,
    ) -> None:
        self._events.append(
            ModelGovernanceEvent(
                event_id=f"{model_id}:{event_type.value}:{len(self._events) + 1}",
                model_id=model_id,
                event_type=event_type,
                previous_status=previous_status,
                new_status=new_status,
                reason=reason,
            )
        )
