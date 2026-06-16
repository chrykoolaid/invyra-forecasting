from dataclasses import dataclass
import os

from invyra_forecasting.constants import Environment


@dataclass(frozen=True)
class ForecastingConfig:
    environment: Environment = Environment.TRAINING
    forecast_horizon_days: int = 30
    demand_lookback_days: int = 30
    target_cover_days: int = 14
    safety_stock_days: int = 3
    snapshot_dir: str = "data/snapshots"
    audit_log_path: str = "data/snapshots/audit_events.jsonl"
    accuracy_log_path: str = "data/snapshots/accuracy_events.jsonl"

    @classmethod
    def from_env(cls) -> "ForecastingConfig":
        env = os.getenv("INVYRA_ENVIRONMENT", Environment.TRAINING.value)
        return cls(
            environment=Environment(env),
            snapshot_dir=os.getenv("INVYRA_FORECAST_SNAPSHOT_DIR", "data/snapshots"),
            audit_log_path=os.getenv("INVYRA_AUDIT_LOG_PATH", "data/snapshots/audit_events.jsonl"),
            accuracy_log_path=os.getenv("INVYRA_ACCURACY_LOG_PATH", "data/snapshots/accuracy_events.jsonl"),
        )
