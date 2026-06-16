from __future__ import annotations

from typing import Any

COMPONENT_NAME = "InventoryItemDetailsForecastPanel"
DEFAULT_TITLE = "Forecast intelligence"
ADVISORY_NOTICE = "Forecasting is advisory. Inventory ledger remains the source of truth."
UNAVAILABLE_TITLE = "Forecast unavailable"
UNAVAILABLE_MESSAGE = "Forecast unavailable. Item Details and stock history remain usable."
LOW_CONFIDENCE_MESSAGE = "Low confidence forecast. Verify movement history, stock accuracy, and supplier lead time before acting."

FIELD_ORDER = [
    "forecast_demand_next_30_days",
    "average_daily_demand",
    "days_of_cover",
    "stockout_risk",
    "overstock_risk",
    "suggested_reorder_quantity",
    "confidence_rating",
    "short_explanation",
]

FIELD_LABELS = {
    "forecast_demand_next_30_days": "Forecast demand next 30 days",
    "average_daily_demand": "Average daily demand",
    "days_of_cover": "Days of cover",
    "stockout_risk": "Stockout risk",
    "overstock_risk": "Overstock risk",
    "suggested_reorder_quantity": "Suggested reorder quantity",
    "confidence_rating": "Confidence",
    "short_explanation": "Explanation",
}

FIELD_HELPERS = {
    "forecast_demand_next_30_days": "Expected demand for the configured forecast window.",
    "average_daily_demand": "Average recent sales-equivalent demand per day.",
    "days_of_cover": "Estimated days available stock can cover demand.",
    "stockout_risk": "Advisory risk based on demand and available stock.",
    "overstock_risk": "Advisory risk based on demand and available stock.",
    "suggested_reorder_quantity": "Advisory quantity only. Does not create or approve a purchase order.",
    "confidence_rating": "Confidence based on movement history, stock quality, and supplier inputs.",
    "short_explanation": "Plain-language reason for the forecast.",
}

ALLOWED_PANEL_STATUSES = {"available", "low_confidence", "unavailable"}


class ItemDetailsForecastViewModelError(ValueError):
    """Raised when a forecast panel response cannot be converted into the UI contract."""


class ItemDetailsForecastViewModelBuilder:
    """Builds a clean UI-facing view model for Inventory Item Details.

    The output is framework-neutral and intentionally excludes raw model internals,
    movement rows, and debug details. It is safe for future Inventory UI wiring.
    """

    def build(self, panel: dict[str, Any]) -> dict[str, Any]:
        status = panel.get("status")
        if status not in ALLOWED_PANEL_STATUSES:
            raise ItemDetailsForecastViewModelError(f"Unsupported panel status: {status}")
        if status == "unavailable":
            return self._build_unavailable(panel)
        return self._build_available_or_low_confidence(panel)

    def _build_available_or_low_confidence(self, panel: dict[str, Any]) -> dict[str, Any]:
        display_fields = panel.get("display_fields") or {}
        status = panel["status"]
        confidence_rating = str(display_fields.get("confidence_rating", "Unknown"))
        warnings = list(panel.get("warnings") or [])
        if status == "low_confidence" and LOW_CONFIDENCE_MESSAGE not in warnings:
            warnings.append(LOW_CONFIDENCE_MESSAGE)
        return {
            "component": COMPONENT_NAME,
            "status": status,
            "title": DEFAULT_TITLE,
            "subtitle": ADVISORY_NOTICE,
            "item_id": panel.get("item_id"),
            "location_id": panel.get("location_id"),
            "environment": panel.get("environment"),
            "status_chip": self._status_chip(status, confidence_rating),
            "fields": self._fields(display_fields),
            "warnings": warnings,
            "snapshot": self._snapshot(panel),
            "actions": self._actions(status),
            "fallback": self._fallback(panel),
            "guardrails": self._guardrails(panel),
            "rendering_rules": self._rendering_rules(),
        }

    def _build_unavailable(self, panel: dict[str, Any]) -> dict[str, Any]:
        return {
            "component": COMPONENT_NAME,
            "status": "unavailable",
            "title": UNAVAILABLE_TITLE,
            "subtitle": panel.get("message") or UNAVAILABLE_MESSAGE,
            "item_id": panel.get("item_id"),
            "location_id": panel.get("location_id"),
            "environment": panel.get("environment"),
            "status_chip": {"label": "Unavailable", "tone": "neutral"},
            "fields": [],
            "warnings": list(panel.get("warnings") or ["Forecast intelligence could not be generated for this item."]),
            "snapshot": {"available": False, "snapshot_id": None, "label": "No forecast evidence available", "generated_at_utc": None},
            "actions": self._actions("unavailable"),
            "fallback": self._fallback(panel),
            "guardrails": self._guardrails(panel),
            "rendering_rules": self._rendering_rules(),
        }

    def _fields(self, display_fields: dict[str, Any]) -> list[dict[str, Any]]:
        fields: list[dict[str, Any]] = []
        for key in FIELD_ORDER:
            if key not in display_fields:
                continue
            value = display_fields[key]
            field: dict[str, Any] = {
                "key": key,
                "label": FIELD_LABELS[key],
                "value": value,
                "helper": FIELD_HELPERS[key],
                "emphasis": "normal",
            }
            if key == "stockout_risk":
                field["chip"] = self._risk_chip(value)
                field["emphasis"] = "high" if str(value).lower() == "high" else "normal"
            elif key == "overstock_risk":
                field["chip"] = self._risk_chip(value)
            elif key == "confidence_rating":
                field["chip"] = self._confidence_chip(str(value))
            fields.append(field)
        return fields

    def _snapshot(self, panel: dict[str, Any]) -> dict[str, Any]:
        snapshot_id = panel.get("snapshot_id")
        return {
            "available": bool(snapshot_id),
            "snapshot_id": snapshot_id,
            "label": "View forecast evidence" if snapshot_id else "No forecast evidence available",
            "generated_at_utc": panel.get("generated_at_utc"),
        }

    def _status_chip(self, status: str, confidence_rating: str) -> dict[str, str]:
        if status == "low_confidence":
            return {"label": "Low confidence", "tone": "warning"}
        confidence = self._confidence_chip(confidence_rating)
        return {"label": confidence["label"], "tone": confidence["tone"]}

    def _risk_chip(self, value: Any) -> dict[str, str]:
        risk = str(value)
        tones = {"High": "danger", "Medium": "warning", "Low": "success"}
        return {"label": risk, "tone": tones.get(risk, "neutral")}

    def _confidence_chip(self, rating: str) -> dict[str, str]:
        tones = {"High": "success", "Medium": "warning", "Low": "warning"}
        return {"label": rating, "tone": tones.get(rating, "neutral")}

    def _actions(self, status: str) -> dict[str, Any]:
        return {
            "refresh_forecast_visible": True,
            "view_snapshot_visible": status != "unavailable",
            "manual_review_visible": True,
            "create_purchase_order_visible": False,
            "approve_purchase_order_visible": False,
            "stock_adjustment_visible": False,
        }

    def _fallback(self, panel: dict[str, Any]) -> dict[str, bool]:
        fallback = panel.get("fallback") or {}
        return {
            "item_details_usable": bool(fallback.get("item_details_usable", True)),
            "stock_history_usable": bool(fallback.get("stock_history_usable", True)),
            "manual_review_available": bool(fallback.get("manual_review_available", True)),
        }

    def _guardrails(self, panel: dict[str, Any]) -> dict[str, bool | str]:
        advisory = panel.get("advisory") or {}
        return {
            "advisory_only": bool(advisory.get("advisory_only", True)),
            "inventory_ledger_source_of_truth": bool(advisory.get("inventory_ledger_source_of_truth", True)),
            "mutates_stock": bool(advisory.get("mutates_stock", False)),
            "creates_purchase_order": bool(advisory.get("creates_purchase_order", False)),
            "approves_purchase_order": bool(advisory.get("approves_purchase_order", False)),
            "notice": ADVISORY_NOTICE,
        }

    def _rendering_rules(self) -> dict[str, bool]:
        return {
            "show_raw_model_internals": False,
            "show_raw_movement_rows": False,
            "duplicate_stock_history": False,
            "duplicate_reorder_review": False,
            "block_item_details_on_forecast_failure": False,
        }


def build_item_details_forecast_view_model(panel: dict[str, Any]) -> dict[str, Any]:
    return ItemDetailsForecastViewModelBuilder().build(panel)
