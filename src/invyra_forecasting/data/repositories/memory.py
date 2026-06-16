from invyra_forecasting.constants import Environment
from invyra_forecasting.schemas import ForecastInputBundle, ForecastSnapshot


class InMemoryForecastRepository:
    """Simple in-memory repository for tests and demos."""

    def __init__(self) -> None:
        self.items = {}
        self.locations = {}
        self.stock_positions = []
        self.movements = []
        self.supplier_profiles = {}
        self.snapshots: dict[str, ForecastSnapshot] = {}

    def add_snapshot(self, snapshot: ForecastSnapshot) -> None:
        self.snapshots[snapshot.snapshot_id] = snapshot

    def get_snapshot(self, snapshot_id: str) -> ForecastSnapshot | None:
        return self.snapshots.get(snapshot_id)

    def build_bundle(self, item_id: str, location_id: str, environment: Environment) -> ForecastInputBundle:
        item = self.items[item_id]
        location = self.locations[location_id]
        stock_position = next(position for position in self.stock_positions if position.item_id == item_id and position.location_id == location_id and position.environment == environment)
        movements = [movement for movement in self.movements if movement.item_id == item_id and movement.location_id == location_id and movement.environment == environment]
        supplier_profile = self.supplier_profiles[item_id]
        return ForecastInputBundle(item=item, location=location, stock_position=stock_position, movements=movements, supplier_profile=supplier_profile, environment=environment)
