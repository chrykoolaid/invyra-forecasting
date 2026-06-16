from __future__ import annotations

from datetime import date, timedelta

from invyra_forecasting.features import days_of_cover
from invyra_forecasting.schemas import ForecastInputBundle, ForecastResult, RiskResult


def _risk_from_cover(cover_days: float | None, lead_time_days: int) -> str:
    if cover_days is None:
        return "Low"
    if cover_days <= max(1, lead_time_days):
        return "High"
    if cover_days <= lead_time_days + 3:
        return "Medium"
    return "Low"


def _overstock_from_cover(cover_days: float | None, target_cover_days: int) -> str:
    if cover_days is None:
        return "Medium"
    if cover_days >= target_cover_days * 3:
        return "High"
    if cover_days >= target_cover_days * 2:
        return "Medium"
    return "Low"


def score_inventory_risk(bundle: ForecastInputBundle, forecast: ForecastResult, target_cover_days: int, anchor_date: date | None = None) -> RiskResult:
    if anchor_date is None:
        anchor_date = date.today()
    cover = days_of_cover(bundle.stock_position.available, forecast.average_daily_demand)
    stockout_risk = _risk_from_cover(cover, bundle.supplier_profile.lead_time_days)
    overstock_risk = _overstock_from_cover(cover, target_cover_days)
    estimated = None if cover is None else (anchor_date + timedelta(days=int(cover))).isoformat()
    return RiskResult(bundle.item.item_id, bundle.location.location_id, None if cover is None else round(cover, 2), stockout_risk, overstock_risk, estimated, bundle.environment)
