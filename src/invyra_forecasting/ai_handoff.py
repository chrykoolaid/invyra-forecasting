from __future__ import annotations

from typing import Any

from invyra_forecasting.models.contracts import ForecastModelOutput


def _risk_to_signal(stockout_risk: str) -> str:
    normalized = stockout_risk.strip().lower()
    if normalized in {"high", "critical"}:
        return "reorder_watch"
    if normalized in {"overstock", "overstock_risk"}:
        return "overstock_watch"
    if normalized in {"slow", "slow_mover"}:
        return "slow_mover"
    return "reorder_watch"


def forecast_output_to_ai_observation(output: ForecastModelOutput) -> dict[str, Any]:
    """Convert a model output into the AI Engine forecasting/review shape.

    This is an advisory handoff only. It does not mutate inventory, create stock
    movements, create purchase orders, or approve purchase orders.
    """
    explanation = " ".join(output.explanation).strip() or "Forecast output requires review."
    return {
        "item_id": output.item_id,
        "location_id": output.location_id,
        "signal": _risk_to_signal(output.stockout_risk),
        "risk": output.stockout_risk,
        "summary": explanation,
        "horizon_days": output.forecast_days,
        "confidence_score": output.confidence,
        "metrics": {
            "forecast_quantity": output.forecast_quantity,
            "projected_days_of_cover": output.projected_days_of_cover,
            "model_name": output.model_name,
            "model_version": output.model_version,
            "evidence_refs": list(output.evidence_refs),
            "advisory_only": output.advisory_only,
            "inventory_source_of_truth_preserved": output.inventory_source_of_truth_preserved,
        },
    }


def build_ai_review_payload(
    *,
    workspace_id: str,
    outputs: list[ForecastModelOutput],
    source_engine: str = "invyra-forecasting",
) -> dict[str, Any]:
    """Build a payload accepted by the AI Engine POST /forecasting/review endpoint."""
    return {
        "workspace_id": workspace_id,
        "source_engine": source_engine,
        "observations": [forecast_output_to_ai_observation(output) for output in outputs],
        "governance": {
            "decision_mode": "review-only",
            "may_modify_inventory": False,
            "may_create_purchase_orders": False,
            "may_approve_purchase_orders": False,
        },
    }
