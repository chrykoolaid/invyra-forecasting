from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class ModelLifecycleState(StrEnum):
    DRAFT = "DRAFT"
    TESTING = "TESTING"
    VALIDATION = "VALIDATION"
    APPROVED = "APPROVED"
    PRODUCTION = "PRODUCTION"
    DEPRECATED = "DEPRECATED"
    ARCHIVED = "ARCHIVED"


@dataclass(frozen=True)
class LifecycleTransition:
    from_state: ModelLifecycleState
    to_state: ModelLifecycleState
    reason: str
    changed_at_utc: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["from_state"] = self.from_state.value
        payload["to_state"] = self.to_state.value
        return payload


@dataclass(frozen=True)
class ModelRegistryEntry:
    model_id: str
    model_name: str
    model_version: str
    forecast_type: str
    lifecycle_state: ModelLifecycleState = ModelLifecycleState.DRAFT
    supported_horizons_days: tuple[int, ...] = (7, 14, 30, 60, 90)
    owner: str | None = None
    description: str | None = None
    strengths: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    performance_summary: dict[str, Any] = field(default_factory=dict)
    transition_history: tuple[LifecycleTransition, ...] = ()
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

    @property
    def is_production_eligible(self) -> bool:
        return self.lifecycle_state in {ModelLifecycleState.APPROVED, ModelLifecycleState.PRODUCTION}

    def transition(self, to_state: ModelLifecycleState, *, reason: str) -> "ModelRegistryEntry":
        if not self._is_allowed_transition(self.lifecycle_state, to_state):
            raise ValueError(f"Invalid model lifecycle transition: {self.lifecycle_state} -> {to_state}")
        transition = LifecycleTransition(self.lifecycle_state, to_state, reason)
        return ModelRegistryEntry(
            model_id=self.model_id,
            model_name=self.model_name,
            model_version=self.model_version,
            forecast_type=self.forecast_type,
            lifecycle_state=to_state,
            supported_horizons_days=self.supported_horizons_days,
            owner=self.owner,
            description=self.description,
            strengths=self.strengths,
            limitations=self.limitations,
            performance_summary=self.performance_summary,
            transition_history=(*self.transition_history, transition),
            advisory_only=self.advisory_only,
            inventory_source_of_truth_preserved=self.inventory_source_of_truth_preserved,
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["lifecycle_state"] = self.lifecycle_state.value
        payload["supported_horizons_days"] = list(self.supported_horizons_days)
        payload["strengths"] = list(self.strengths)
        payload["limitations"] = list(self.limitations)
        payload["transition_history"] = [transition.to_dict() for transition in self.transition_history]
        return payload

    def _is_allowed_transition(self, from_state: ModelLifecycleState, to_state: ModelLifecycleState) -> bool:
        allowed = {
            ModelLifecycleState.DRAFT: {ModelLifecycleState.TESTING, ModelLifecycleState.ARCHIVED},
            ModelLifecycleState.TESTING: {ModelLifecycleState.VALIDATION, ModelLifecycleState.DRAFT, ModelLifecycleState.ARCHIVED},
            ModelLifecycleState.VALIDATION: {ModelLifecycleState.APPROVED, ModelLifecycleState.TESTING, ModelLifecycleState.ARCHIVED},
            ModelLifecycleState.APPROVED: {ModelLifecycleState.PRODUCTION, ModelLifecycleState.DEPRECATED, ModelLifecycleState.ARCHIVED},
            ModelLifecycleState.PRODUCTION: {ModelLifecycleState.DEPRECATED},
            ModelLifecycleState.DEPRECATED: {ModelLifecycleState.ARCHIVED},
            ModelLifecycleState.ARCHIVED: set(),
        }
        return to_state in allowed[from_state]


class ModelLifecycleRegistry:
    def __init__(self) -> None:
        self._entries: dict[str, ModelRegistryEntry] = {}

    def register(self, entry: ModelRegistryEntry) -> None:
        if entry.model_id in self._entries:
            raise ValueError(f"Model already registered: {entry.model_id}")
        self._entries[entry.model_id] = entry

    def get(self, model_id: str) -> ModelRegistryEntry:
        try:
            return self._entries[model_id]
        except KeyError as exc:
            raise KeyError(f"Unknown model: {model_id}") from exc

    def transition(self, model_id: str, to_state: ModelLifecycleState, *, reason: str) -> ModelRegistryEntry:
        updated = self.get(model_id).transition(to_state, reason=reason)
        self._entries[model_id] = updated
        return updated

    def eligible(self, *, forecast_type: str, forecast_horizon_days: int) -> tuple[ModelRegistryEntry, ...]:
        return tuple(
            entry
            for entry in self._entries.values()
            if entry.forecast_type == forecast_type
            and forecast_horizon_days in entry.supported_horizons_days
            and entry.is_production_eligible
        )

    def all(self) -> tuple[ModelRegistryEntry, ...]:
        return tuple(self._entries.values())

    def to_dict(self) -> dict[str, Any]:
        return {model_id: entry.to_dict() for model_id, entry in self._entries.items()}
