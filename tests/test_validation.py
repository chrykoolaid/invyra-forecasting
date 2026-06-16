from datetime import date

import pytest

from invyra_forecasting.constants import Environment, MovementType
from invyra_forecasting.data.validation import ValidationError, validate_forecast_input
from invyra_forecasting.schemas import ForecastInputBundle, Item, Location, StockMovement, StockPosition, SupplierProfile


def test_environment_mixing_is_blocked():
    bundle = ForecastInputBundle(
        item=Item("ITEM-001", "SKU-1", "Coffee", "Grocery"),
        location=Location("LOC-001", "Training Store"),
        stock_position=StockPosition("ITEM-001", "LOC-001", on_hand=10, environment=Environment.TRAINING),
        movements=[StockMovement("MOV-1", "ITEM-001", "LOC-001", date(2026, 6, 1), MovementType.POS_SALE, 1, Environment.LIVE)],
        supplier_profile=SupplierProfile("SUP-001", "ITEM-001", lead_time_days=5),
        environment=Environment.TRAINING,
    )
    with pytest.raises(ValidationError, match="Environment mismatch"):
        validate_forecast_input(bundle)
