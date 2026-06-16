from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from invyra_forecasting.constants import SALES_EQUIVALENT_MOVEMENTS
from invyra_forecasting.schemas import StockMovement


def demand_movements(movements: list[StockMovement]) -> list[StockMovement]:
    return [movement for movement in movements if movement.movement_type in SALES_EQUIVALENT_MOVEMENTS]


def demand_quantity_by_day(movements: list[StockMovement], lookback_days: int, anchor_date: date | None = None) -> dict[date, float]:
    if lookback_days <= 0:
        raise ValueError("lookback_days must be positive")
    if anchor_date is None:
        anchor_date = max((m.movement_date for m in movements), default=date.today())
    start_date = anchor_date - timedelta(days=lookback_days - 1)
    buckets: dict[date, float] = defaultdict(float)
    for movement in demand_movements(movements):
        if start_date <= movement.movement_date <= anchor_date:
            buckets[movement.movement_date] += movement.quantity
    return {start_date + timedelta(days=offset): buckets[start_date + timedelta(days=offset)] for offset in range(lookback_days)}


def average_daily_demand(movements: list[StockMovement], lookback_days: int, anchor_date: date | None = None) -> float:
    daily = demand_quantity_by_day(movements, lookback_days, anchor_date)
    return sum(daily.values()) / lookback_days


def moving_average_forecast(movements: list[StockMovement], lookback_days: int, horizon_days: int, anchor_date: date | None = None) -> float:
    return average_daily_demand(movements, lookback_days, anchor_date) * horizon_days


def weighted_moving_average_forecast(movements: list[StockMovement], lookback_days: int, horizon_days: int, anchor_date: date | None = None) -> float:
    daily = list(demand_quantity_by_day(movements, lookback_days, anchor_date).values())
    if not daily:
        return 0.0
    weights = list(range(1, len(daily) + 1))
    weighted_average = sum(value * weight for value, weight in zip(daily, weights)) / sum(weights)
    return weighted_average * horizon_days


def trend_adjustment(movements: list[StockMovement], lookback_days: int, anchor_date: date | None = None) -> float:
    daily = list(demand_quantity_by_day(movements, lookback_days, anchor_date).values())
    if len(daily) < 6:
        return 1.0
    midpoint = len(daily) // 2
    first_average = sum(daily[:midpoint]) / len(daily[:midpoint])
    second_average = sum(daily[midpoint:]) / len(daily[midpoint:])
    if first_average <= 0 and second_average <= 0:
        return 1.0
    if first_average <= 0:
        return 1.2
    return max(0.8, min(1.25, second_average / first_average))


def days_of_cover(available_stock: float, average_daily_demand_value: float) -> float | None:
    if average_daily_demand_value <= 0:
        return None
    return available_stock / average_daily_demand_value
