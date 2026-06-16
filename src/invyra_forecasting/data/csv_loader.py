from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from invyra_forecasting.constants import Environment, MovementType
from invyra_forecasting.schemas import Item, Location, StockMovement, StockPosition, SupplierProfile


def _read_csv(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_items(path: str | Path) -> dict[str, Item]:
    return {row["item_id"]: Item(row["item_id"], row["sku"], row["name"], row["category"], row.get("unit_of_measure") or "unit", int(row.get("minimum_order_quantity") or 1)) for row in _read_csv(path)}


def load_locations(path: str | Path) -> dict[str, Location]:
    return {row["location_id"]: Location(row["location_id"], row["name"], row.get("location_type") or "STORE") for row in _read_csv(path)}


def load_stock_positions(path: str | Path) -> list[StockPosition]:
    return [StockPosition(row["item_id"], row["location_id"], float(row["on_hand"]), float(row.get("reserved") or 0), Environment(row.get("environment") or Environment.TRAINING.value)) for row in _read_csv(path)]


def load_movements(path: str | Path) -> list[StockMovement]:
    return [StockMovement(row["movement_id"], row["item_id"], row["location_id"], date.fromisoformat(row["movement_date"]), MovementType(row["movement_type"]), float(row["quantity"]), Environment(row.get("environment") or Environment.TRAINING.value)) for row in _read_csv(path)]


def load_supplier_profiles(path: str | Path) -> dict[str, SupplierProfile]:
    return {row["item_id"]: SupplierProfile(row["supplier_id"], row["item_id"], int(row["lead_time_days"]), int(row.get("lead_time_variability_days") or 0), int(row.get("minimum_order_quantity") or 1)) for row in _read_csv(path)}
