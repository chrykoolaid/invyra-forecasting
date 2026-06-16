from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from invyra_forecasting.features import average_daily_demand, moving_average_forecast, trend_adjustment, weighted_moving_average_forecast
from invyra_forecasting.schemas import ForecastInputBundle, ForecastResult


@dataclass(frozen=True)
class SimpleDemandForecaster:
    lookback_days: int = 30
    horizon_days: int = 30
    method: str = "weighted_moving_average_with_trend"

    def forecast(self, bundle: ForecastInputBundle, anchor_date: date | None = None) -> ForecastResult:
        average_daily = average_daily_demand(bundle.movements, self.lookback_days, anchor_date)
        moving_average = moving_average_forecast(bundle.movements, self.lookback_days, self.horizon_days, anchor_date)
        weighted_average = weighted_moving_average_forecast(bundle.movements, self.lookback_days, self.horizon_days, anchor_date)
        adjustment = trend_adjustment(bundle.movements, self.lookback_days, anchor_date)
        forecast_quantity = ((moving_average * 0.35) + (weighted_average * 0.65)) * adjustment
        return ForecastResult(bundle.item.item_id, bundle.location.location_id, self.horizon_days, round(max(0.0, forecast_quantity), 2), round(max(0.0, average_daily), 4), self.method, bundle.environment)
