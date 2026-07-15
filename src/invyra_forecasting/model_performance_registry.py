from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Iterable
from uuid import uuid4

from invyra_forecasting.api.tenant_namespace import current_namespace

MODEL_PERFORMANCE_REGISTRY_SCHEMA_VERSION = "1.0.0"


class ModelLifecycleStatus(str, Enum):
    EXPERIMENTAL = "experimental"
    ACTIVE = "active"
    OBSERVATION = "observation"
    DEPRECATED = "deprecated"
    RETIRED = "retired"


@dataclass(frozen=True)
class ModelPerformanceRegistryEntry:
    registry_id: str
    model_name: str
    model_version: str
    lifecycle_status: ModelLifecycleStatus
    supported_forecast_horizons: tuple[int, ...]
    supported_demand_profiles: tuple[str, ...]
    namespace: str
    registered_at_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    schema_version: str = MODEL_PERFORMANCE_REGISTRY_SCHEMA_VERSION
    advisory_only: bool = True
    read_only: bool = True
    inventory_source_of_truth_preserved: bool = True

    def __post_init__(self) -> None:
        for field_name, value in {
            "registry_id": self.registry_id,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "namespace": self.namespace,
        }.items():
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} is required")
        if not self.supported_forecast_horizons:
            raise ValueError("at least one supported forecast horizon is required")
        if any(
            not isinstance(value, int) or isinstance(value, bool) or value < 1
            for value in self.supported_forecast_horizons
        ):
            raise ValueError("supported forecast horizons must contain positive integers")
        if tuple(sorted(set(self.supported_forecast_horizons))) != self.supported_forecast_horizons:
            raise ValueError("supported forecast horizons must be unique and sorted")
        if any(
            not isinstance(value, str) or not value.strip()
            for value in self.supported_demand_profiles
        ):
            raise ValueError("supported demand profiles must contain non-empty strings")
        if tuple(dict.fromkeys(self.supported_demand_profiles)) != self.supported_demand_profiles:
            raise ValueError("supported demand profiles must be unique")
        try:
            parsed = datetime.fromisoformat(self.registered_at_utc)
        except (TypeError, ValueError) as exc:
            raise ValueError("registered_at_utc must be a valid ISO-8601 timestamp") from exc
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("registered_at_utc must include a UTC offset")
        if self.schema_version != MODEL_PERFORMANCE_REGISTRY_SCHEMA_VERSION:
            raise ValueError("unsupported model performance registry schema version")
        if not self.advisory_only or not self.read_only:
            raise ValueError("model registry entries must remain advisory-only and read-only")
        if not self.inventory_source_of_truth_preserved:
            raise ValueError("inventory source of truth must be preserved")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["lifecycle_status"] = self.lifecycle_status.value
        payload["supported_forecast_horizons"] = list(self.supported_forecast_horizons)
        payload["supported_demand_profiles"] = list(self.supported_demand_profiles)
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ModelPerformanceRegistryEntry":
        return cls(
            **{
                **payload,
                "lifecycle_status": ModelLifecycleStatus(payload["lifecycle_status"]),
                "supported_forecast_horizons": tuple(
                    payload.get("supported_forecast_horizons", ())
                ),
                "supported_demand_profiles": tuple(
                    payload.get("supported_demand_profiles", ())
                ),
            }
        )


class InMemoryModelPerformanceRegistry:
    """Tenant-isolated, append-only model metadata registry."""

    def __init__(self, entries: Iterable[ModelPerformanceRegistryEntry] = ()) -> None:
        self._entries_by_namespace: dict[str, dict[str, ModelPerformanceRegistryEntry]] = {}
        for entry in entries:
            self._append_loaded(entry)

    def _entries(self) -> dict[str, ModelPerformanceRegistryEntry]:
        return self._entries_by_namespace.setdefault(current_namespace(), {})

    def _append_loaded(self, entry: ModelPerformanceRegistryEntry) -> None:
        entries = self._entries_by_namespace.setdefault(entry.namespace, {})
        self._validate_unique(entry, entries.values())
        entries[entry.registry_id] = entry

    @staticmethod
    def _validate_unique(
        entry: ModelPerformanceRegistryEntry,
        existing: Iterable[ModelPerformanceRegistryEntry],
    ) -> None:
        if any(item.registry_id == entry.registry_id for item in existing):
            raise ValueError(f"model registry entry already exists: {entry.registry_id}")
        if any(
            (item.model_name, item.model_version)
            == (entry.model_name, entry.model_version)
            for item in existing
        ):
            raise ValueError(
                f"model version already registered: {entry.model_name} {entry.model_version}"
            )

    def append(self, entry: ModelPerformanceRegistryEntry) -> ModelPerformanceRegistryEntry:
        if entry.namespace != current_namespace():
            raise ValueError(
                "model registry namespace must match the active tenant namespace"
            )
        entries = self._entries()
        self._validate_unique(entry, entries.values())
        entries[entry.registry_id] = entry
        return entry

    def get(self, registry_id: str) -> ModelPerformanceRegistryEntry | None:
        return self._entries().get(registry_id)

    def for_model(self, model_name: str) -> tuple[ModelPerformanceRegistryEntry, ...]:
        return tuple(
            sorted(
                (
                    entry
                    for entry in self._entries().values()
                    if entry.model_name == model_name
                ),
                key=lambda entry: (
                    entry.registered_at_utc,
                    entry.model_version,
                    entry.registry_id,
                ),
            )
        )

    def all(self) -> tuple[ModelPerformanceRegistryEntry, ...]:
        return tuple(
            sorted(
                self._entries().values(),
                key=lambda entry: (
                    entry.model_name,
                    entry.model_version,
                    entry.registry_id,
                ),
            )
        )


class JsonlModelPerformanceRegistry(InMemoryModelPerformanceRegistry):
    """Append-only JSONL storage with tenant-safe reconstruction."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        entries: list[ModelPerformanceRegistryEntry] = []
        if self._path.exists():
            for line in self._path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    entries.append(
                        ModelPerformanceRegistryEntry.from_dict(json.loads(line))
                    )
        super().__init__(entries)

    def append(self, entry: ModelPerformanceRegistryEntry) -> ModelPerformanceRegistryEntry:
        saved = super().append(entry)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(saved.to_dict(), sort_keys=True) + "\n")
        return saved


class ModelPerformanceRegistryService:
    def __init__(
        self,
        repository: InMemoryModelPerformanceRegistry | None = None,
    ) -> None:
        self._repository = repository or InMemoryModelPerformanceRegistry()

    def register(
        self,
        *,
        model_name: str,
        model_version: str,
        lifecycle_status: ModelLifecycleStatus,
        supported_forecast_horizons: Iterable[int],
        supported_demand_profiles: Iterable[str] = (),
        registry_id: str | None = None,
        registered_at_utc: str | None = None,
    ) -> ModelPerformanceRegistryEntry:
        values: dict[str, Any] = {}
        if registered_at_utc is not None:
            values["registered_at_utc"] = registered_at_utc
        entry = ModelPerformanceRegistryEntry(
            registry_id=registry_id or str(uuid4()),
            model_name=model_name.strip(),
            model_version=model_version.strip(),
            lifecycle_status=lifecycle_status,
            supported_forecast_horizons=tuple(
                sorted(set(supported_forecast_horizons))
            ),
            supported_demand_profiles=tuple(
                dict.fromkeys(profile.strip() for profile in supported_demand_profiles)
            ),
            namespace=current_namespace(),
            **values,
        )
        return self._repository.append(entry)

    def get(self, registry_id: str) -> ModelPerformanceRegistryEntry | None:
        return self._repository.get(registry_id)

    def for_model(self, model_name: str) -> tuple[ModelPerformanceRegistryEntry, ...]:
        return self._repository.for_model(model_name)

    def all(self) -> tuple[ModelPerformanceRegistryEntry, ...]:
        return self._repository.all()
