from __future__ import annotations

from datetime import date
from pathlib import Path

from invyra_forecasting.config import ForecastingConfig
from invyra_forecasting.constants import Environment
from invyra_forecasting.data.csv_loader import load_items, load_locations, load_movements, load_stock_positions, load_supplier_profiles
from invyra_forecasting.schemas import ForecastInputBundle
from invyra_forecasting.services import ForecastingService


def main() -> None:
    base = Path("data/sample")
    items = load_items(base / "items.csv")
    locations = load_locations(base / "locations.csv")
    stock_positions = load_stock_positions(base / "stock_positions.csv")
    movements = load_movements(base / "movements.csv")
    suppliers = load_supplier_profiles(base / "supplier_profiles.csv")
    item_id = "ITEM-001"
    location_id = "LOC-001"
    environment = Environment.TRAINING
    stock_position = next(s for s in stock_positions if s.item_id == item_id and s.location_id == location_id and s.environment == environment)
    bundle = ForecastInputBundle(
        item=items[item_id],
        location=locations[location_id],
        stock_position=stock_position,
        movements=[m for m in movements if m.item_id == item_id and m.location_id == location_id and m.environment == environment],
        supplier_profile=suppliers[item_id],
        environment=environment,
    )
    service = ForecastingService(ForecastingConfig(environment=environment, snapshot_dir="data/snapshots"))
    snapshot = service.run_item_forecast(bundle, actor="local_demo", anchor_date=date(2026, 6, 16), write_snapshot=True)
    print("Invyra Forecasting Engine — Local Demo")
    print("--------------------------------------")
    print(f"Item: {bundle.item.name}")
    print(f"Location: {bundle.location.name}")
    print(f"Demand forecast next {snapshot.forecast.forecast_horizon_days} days: {snapshot.forecast.forecast_quantity} units")
    print(f"Days of cover: {snapshot.risk.days_of_cover}")
    print(f"Stockout risk: {snapshot.risk.stockout_risk}")
    print(f"Overstock risk: {snapshot.risk.overstock_risk}")
    print(f"Suggested reorder quantity: {snapshot.recommendation.suggested_reorder_quantity} units")
    print(f"Confidence: {snapshot.confidence.rating}")
    print(f"Reason: {snapshot.explanation.summary}")
    print(f"Snapshot ID: {snapshot.snapshot_id}")


if __name__ == "__main__":
    main()
