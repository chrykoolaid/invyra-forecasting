from datetime import date, timedelta

from invyra_forecasting.constants import SALES_EQUIVALENT_MOVEMENTS
from invyra_forecasting.schemas import ConfidenceResult, ForecastInputBundle


def score_confidence(bundle: ForecastInputBundle, lookback_days: int, anchor_date: date | None = None) -> ConfidenceResult:
    if anchor_date is None:
        anchor_date = max((m.movement_date for m in bundle.movements), default=date.today())
    start_date = anchor_date - timedelta(days=lookback_days - 1)
    demand_records = [movement for movement in bundle.movements if movement.movement_type in SALES_EQUIVALENT_MOVEMENTS and start_date <= movement.movement_date <= anchor_date]
    active_days = len({movement.movement_date for movement in demand_records})
    reasons: list[str] = []
    score = 100.0
    if len(demand_records) < 5:
        score -= 35
        reasons.append("Limited sales-equivalent movement history.")
    if active_days < 7:
        score -= 20
        reasons.append("Demand appears sparse across the lookback window.")
    if bundle.stock_position.on_hand < 0:
        score -= 25
        reasons.append("Stock on hand is negative and should be corrected.")
    if bundle.supplier_profile.lead_time_variability_days >= 3:
        score -= 10
        reasons.append("Supplier lead time variability is elevated.")
    score = max(0.0, min(100.0, score))
    rating = "High" if score >= 75 else "Medium" if score >= 45 else "Low"
    if not reasons:
        reasons.append("Movement history and supplier inputs are sufficient for Phase 1.")
    return ConfidenceResult(rating=rating, score=round(score, 2), reasons=reasons)
