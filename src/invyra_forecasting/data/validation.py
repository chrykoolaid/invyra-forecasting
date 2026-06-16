from invyra_forecasting.constants import Environment
from invyra_forecasting.schemas import ForecastInputBundle, StockMovement


class ValidationError(ValueError):
    """Raised when forecasting input data violates governance or contract rules."""


def validate_environment(expected: Environment, actual: Environment, context: str) -> None:
    if expected != actual:
        raise ValidationError(f"Environment mismatch in {context}: expected {expected.value}, got {actual.value}")


def validate_movements_environment(expected: Environment, movements: list[StockMovement]) -> None:
    for movement in movements:
        validate_environment(expected, movement.environment, f"movement {movement.movement_id}")


def validate_forecast_input(bundle: ForecastInputBundle) -> None:
    if not bundle.item.item_id:
        raise ValidationError("item_id is required")
    if not bundle.location.location_id:
        raise ValidationError("location_id is required")
    if bundle.stock_position.item_id != bundle.item.item_id:
        raise ValidationError("stock_position item_id does not match item")
    if bundle.stock_position.location_id != bundle.location.location_id:
        raise ValidationError("stock_position location_id does not match location")
    if bundle.supplier_profile.item_id != bundle.item.item_id:
        raise ValidationError("supplier profile item_id does not match item")
    validate_environment(bundle.environment, bundle.stock_position.environment, "stock_position")
    validate_movements_environment(bundle.environment, bundle.movements)
    for movement in bundle.movements:
        if movement.item_id != bundle.item.item_id:
            raise ValidationError(f"movement {movement.movement_id} item_id does not match item")
        if movement.location_id != bundle.location.location_id:
            raise ValidationError(f"movement {movement.movement_id} location_id does not match location")
        if movement.quantity < 0:
            raise ValidationError(f"movement {movement.movement_id} quantity cannot be negative")
    if bundle.supplier_profile.lead_time_days < 0:
        raise ValidationError("supplier lead_time_days cannot be negative")
    if bundle.supplier_profile.minimum_order_quantity < 1:
        raise ValidationError("supplier minimum_order_quantity must be at least 1")
