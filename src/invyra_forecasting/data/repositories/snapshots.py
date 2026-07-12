from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any
from urllib.parse import quote

from invyra_forecasting.api.tenant_namespace import DEFAULT_NAMESPACE, current_namespace
from invyra_forecasting.schemas import ForecastSnapshot


class FileSnapshotRepository:
    """File-backed forecast snapshot repository for Phase 1D.

    This local repository is intentionally simple and replaceable. It provides
    readback and traceability without introducing database infrastructure yet.
    Named tenant namespaces are isolated in encoded subdirectories, while the
    default namespace retains the legacy root-directory layout.
    """

    def __init__(self, snapshot_dir: str | Path = "data/snapshots") -> None:
        self.snapshot_dir = Path(snapshot_dir)

    def save(self, snapshot: ForecastSnapshot) -> Path:
        namespace_dir = self.namespace_dir()
        namespace_dir.mkdir(parents=True, exist_ok=True)
        path = self.path_for(snapshot.snapshot_id)
        path.write_text(json.dumps(asdict(snapshot), indent=2, default=str), encoding="utf-8")
        return path

    def get(self, snapshot_id: str) -> dict[str, Any] | None:
        path = self.path_for(snapshot_id)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def exists(self, snapshot_id: str) -> bool:
        return self.path_for(snapshot_id).exists()

    def list_snapshot_ids(self) -> list[str]:
        namespace_dir = self.namespace_dir()
        if not namespace_dir.exists():
            return []
        return sorted(path.stem for path in namespace_dir.glob("*.json"))

    def namespace_dir(self) -> Path:
        namespace = current_namespace()
        if namespace == DEFAULT_NAMESPACE:
            return self.snapshot_dir
        return self.snapshot_dir / quote(namespace, safe="-_.")

    def path_for(self, snapshot_id: str) -> Path:
        safe_id = snapshot_id.replace("/", "_").replace("\\", "_")
        return self.namespace_dir() / f"{safe_id}.json"
