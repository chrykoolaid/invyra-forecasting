from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from invyra_forecasting.accuracy.entities import ForecastAccuracyResult
from invyra_forecasting.constants import Environment


class JsonlAccuracyStore:
    """Append-only JSONL store for forecast accuracy evaluations."""

    def __init__(self, accuracy_log_path: str | Path = "data/snapshots/accuracy_events.jsonl") -> None:
        self.accuracy_log_path = Path(accuracy_log_path)

    def append(self, result: ForecastAccuracyResult) -> Path:
        self.accuracy_log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.accuracy_log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(result), default=str) + "\n")
        return self.accuracy_log_path

    def list_results(
        self,
        limit: int | None = 100,
        item_id: str | None = None,
        location_id: str | None = None,
        environment: Environment | str | None = None,
        forecast_snapshot_id: str | None = None,
    ) -> list[dict[str, Any]]:
        if not self.accuracy_log_path.exists():
            return []
        environment_value = environment.value if isinstance(environment, Environment) else environment
        results: list[dict[str, Any]] = []
        for line in self.accuracy_log_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            result = json.loads(line)
            if item_id and result.get("item_id") != item_id:
                continue
            if location_id and result.get("location_id") != location_id:
                continue
            if environment_value and result.get("environment") != environment_value:
                continue
            if forecast_snapshot_id and result.get("forecast_snapshot_id") != forecast_snapshot_id:
                continue
            results.append(result)
        if limit is None or limit <= 0:
            return results
        return results[-limit:]
