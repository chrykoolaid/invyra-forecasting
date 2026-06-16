from __future__ import annotations

import math

from invyra_forecasting.schemas import ForecastInputBundle, ForecastResult, RecommendationResult, RiskResult


def _round_to_moq(quantity: float, minimum_order_quantity: int) -> int:
    minimum_order_quantity = max(1, int(minimum_order_quantity))
    if quantity <= 0:
        return 0
    return int(math.ceil(quantity / minimum_order_quantity) * minimum_order_quantity)


def build_reorder_recommendation(bundle: ForecastInputBundle, forecast: ForecastResult, risk: RiskResult, safety_stock_days: int, target_cover_days: int) -> RecommendationResult:
    lead_time_days = bundle.supplier_profile.lead_time_days
    lead_time_buffer_days = lead_time_days + bundle.supplier_profile.lead_time_variability_days
    required_cover_days = max(target_cover_days, lead_time_buffer_days + safety_stock_days)
    required_stock = forecast.average_daily_demand * required_cover_days
    gap = required_stock - bundle.stock_position.available
    suggested = _round_to_moq(gap, bundle.supplier_profile.minimum_order_quantity)
    reorder_needed = suggested > 0 or risk.stockout_risk in {"High", "Medium"}
    urgency = "High" if risk.stockout_risk == "High" else "Medium" if risk.stockout_risk == "Medium" or suggested > 0 else "Low"
    return RecommendationResult(bundle.item.item_id, bundle.location.location_id, reorder_needed, suggested, urgency, lead_time_days, bundle.environment)
