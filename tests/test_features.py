from datetime import date

from invyra_forecasting.constants import Environment, MovementType
from invyra_forecasting.features import average_daily_demand, days_of_cover
from invyra_forecasting.schemas import StockMovement


def test_average_daily_demand_uses_sales_equivalent_only():
    movements = [
        StockMovement("S1", "I1", "L1", date(2026, 6, 1), MovementType.POS_SALE, 3, Environment.TEST),
        StockMovement("R1", "I1", "L1", date(2026, 6, 1), MovementType.RECEIPT, 100, Environment.TEST),
        StockMovement("S2", "I1", "L1", date(2026, 6, 2), MovementType.WASTAGE, 2, Environment.TEST),
    ]
    assert average_daily_demand(movements, 2, anchor_date=date(2026, 6, 2)) == 2.5


def test_days_of_cover_returns_none_for_no_demand():
    assert days_of_cover(10, 0) is None
    assert days_of_cover(10, 2) == 5
