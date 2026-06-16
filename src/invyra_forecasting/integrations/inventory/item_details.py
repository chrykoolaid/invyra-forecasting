from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from invyra_forecasting.api.serializers import to_primitive
from invyra_forecasting.constants import Environment
from invyra_forecasting.data.validation import ValidationError
from invyra_forecasting.integrations.inventory.adapter import (
    InventoryAdapterMappingError,
    InventoryForecastMapper,
    InventoryForecastMappingInput,
)
from invyra_forecasting.services import ForecastingService

LOW_CONFIDENCE_VERIFICATION_MESSAGE = "Low confidence forecast. Verify movement history, stock accuracy, and supplier lead time before acting."
UNAVAILABLE_MESSAGE = "Forecast unavailable. Item Details and stock history remain usable."
PANEL_NAME = "inventory_item_details_forecast"


class ItemDetailsForecastBoundary:
    """Read-only service boundary for the Inventory Item Details forecast panel.

    This boundary is intentionally UI-safe: callers receive a stable panel contract even when
    mapping, validation, snapshot, or engine execution fails. Forecasting remains advisory and
    cannot mutate Inventory records or create purchasing actions.
    """

    def __init__(self, service: ForecastingService | None = None, mapper: InventoryForecastMapper | None = None) -> None:
        self.service = service or ForecastingService()
        self.mapper = mapper or InventoryForecastMapper()

    def build_panel(self, source: InventoryForecastMappingInput, *, persist_snapshot: bool = True) -> dict[str, Any]:
        try:
            request = self.mapper.map_to_forecast_request(source)
            request.write_snapshot = persist_snapshot
            snapshot = self.service.run_item_forecast(
                request.to_bundle(),
                actor=request.actor,
                anchor_date=request.anchor_date,
                write_snapshot=persist_snapshot,
            )
            status = "low_confidence" if snapshot.confidence.rating == "Low" else "available"
            warnings = list(snapshot.explanation.warnings)
            if status == "low_confidence":
                warnings.append(LOW_CONFIDENCE_VERIFICATION_MESSAGE)
            snapshot_persisted = self.service.snapshot_repository.exists(snapshot.snapshot_id) if persist_snapshot else False
            return {
                "panel": PANEL_NAME,
                "status": status,
                "environment": snapshot.forecast.environment.value,
                "item_id": snapshot.forecast.item_id,
                "location_id": snapshot.forecast.location_id,
                "generated_at_utc": snapshot.created_at_utc,
                "snapshot_id": snapshot.snapshot_id,
                "snapshot_persisted": snapshot_persisted,
                "display_fields": self._display_fields(snapshot),
                "warnings": warnings,
                "advisory": self._advisory_flags(),
                "fallback": self._fallback_contract(usable=True),
            }
        except (InventoryAdapterMappingError, ValidationError, ValueError) as exc:
            return self._unavailable(reason=str(exc), source=source)
        except Exception as exc:  # pragma: no cover - exercised through injected test doubles
            return self._unavailable(reason=f"Forecast service failure: {exc}", source=source)

    def build_panel_from_mappings(
        self,
        *,
        item: Mapping[str, Any],
        location: Mapping[str, Any],
        stock_position: Mapping[str, Any],
        movements: Sequence[Mapping[str, Any]],
        supplier_profile: Mapping[str, Any],
        environment: Environment | str = Environment.TRAINING,
        actor: str = "item_details_panel",
        persist_snapshot: bool = True,
        **options: Any,
    ) -> dict[str, Any]:
        try:
            source = InventoryForecastMappingInput.from_mappings(
                item=item,
                location=location,
                stock_position=stock_position,
                movements=movements,
                supplier_profile=supplier_profile,
                environment=environment,
                actor=actor,
                write_snapshot=persist_snapshot,
                **options,
            )
        except (InventoryAdapterMappingError, ValueError) as exc:
            return self._unavailable(reason=str(exc), source=None, environment=environment)
        return self.build_panel(source, persist_snapshot=persist_snapshot)

    def read_snapshot_evidence(self, snapshot_id: str) -> dict[str, Any]:
        snapshot = self.service.get_snapshot(snapshot_id)
        if snapshot is None:
            return {
                "status": "unavailable",
                "snapshot_id": snapshot_id,
                "message": "Forecast snapshot evidence was not found.",
                "fallback": self._fallback_contract(usable=True),
            }
        return {
            "status": "available",
            "snapshot_id": snapshot_id,
            "snapshot": snapshot,
            "advisory": self._advisory_flags(),
        }

    def _display_fields(self, snapshot: Any) -> dict[str, Any]:
        return {
            "forecast_demand_next_30_days": to_primitive(snapshot.forecast.forecast_quantity),
            "average_daily_demand": to_primitive(snapshot.forecast.average_daily_demand),
            "days_of_cover": to_primitive(snapshot.risk.days_of_cover),
            "stockout_risk": to_primitive(snapshot.risk.stockout_risk),
            "overstock_risk": to_primitive(snapshot.risk.overstock_risk),
            "suggested_reorder_quantity": to_primitive(snapshot.recommendation.suggested_reorder_quantity),
            "confidence_rating": to_primitive(snapshot.confidence.rating),
            "confidence_score": to_primitive(snapshot.confidence.score),
            "short_explanation": to_primitive(snapshot.explanation.summary),
            "last_snapshot_id": snapshot.snapshot_id,
            "generated_at_utc": snapshot.created_at_utc,
        }

    def _unavailable(self, *, reason: str, source: InventoryForecastMappingInput | None, environment: Environment | str | None = None) -> dict[str, Any]:
        item_id = source.item.item_id if source is not None else None
        location_id = source.location.location_id if source is not None else None
        env = source.environment if source is not None else environment
        env_value = env.value if isinstance(env, Environment) else env
        return {
            "panel": PANEL_NAME,
            "status": "unavailable",
            "environment": env_value,
            "item_id": item_id,
            "location_id": location_id,
            "generated_at_utc": None,
            "snapshot_id": None,
            "snapshot_persisted": False,
            "display_fields": None,
            "message": UNAVAILABLE_MESSAGE,
            "reason": reason,
            "warnings": ["Forecast intelligence could not be generated for this item."],
            "recommended_action": "Use existing Item Details and Stock History, then retry forecasting after source data is corrected.",
            "advisory": self._advisory_flags(),
            "fallback": self._fallback_contract(usable=True),
        }

    def _fallback_contract(self, *, usable: bool) -> dict[str, bool]:
        return {
            "item_details_usable": usable,
            "stock_history_usable": usable,
            "manual_review_available": usable,
        }

    def _advisory_flags(self) -> dict[str, bool]:
        return {
            "advisory_only": True,
            "inventory_ledger_source_of_truth": True,
            "mutates_stock": False,
            "creates_purchase_order": False,
            "approves_purchase_order": False,
        }
