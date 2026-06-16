from invyra_forecasting.schemas import ConfidenceResult, ExplanationResult, ForecastInputBundle, ForecastResult, RecommendationResult, RiskResult


def build_explanation(bundle: ForecastInputBundle, forecast: ForecastResult, risk: RiskResult, recommendation: RecommendationResult, confidence: ConfidenceResult) -> ExplanationResult:
    drivers = [
        f"Forecast demand over {forecast.forecast_horizon_days} days is {forecast.forecast_quantity} units.",
        f"Average daily demand is {forecast.average_daily_demand} units.",
        f"Available stock is {bundle.stock_position.available} units.",
        f"Supplier lead time is {bundle.supplier_profile.lead_time_days} days.",
    ]
    warnings: list[str] = []
    if confidence.rating == "Low":
        warnings.append("Low confidence: verify movement history and stock data before acting.")
    if risk.stockout_risk == "High":
        warnings.append("High stockout risk: current stock may not cover supplier lead time.")
    if risk.overstock_risk == "High":
        warnings.append("High overstock risk: current stock appears above expected demand cover.")
    summary = f"Suggested reorder quantity is {recommendation.suggested_reorder_quantity} units with {recommendation.urgency.lower()} urgency." if recommendation.reorder_needed else "No reorder is suggested by the Phase 1 explainable forecast."
    return ExplanationResult(summary=summary, drivers=drivers, warnings=warnings)
