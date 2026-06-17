from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BLUEPRINT = ROOT / "render.yaml"

REQUIRED_MARKERS = [
    "type: web",
    "runtime: docker",
    "healthCheckPath: /health",
    "INVYRA_FORECASTING_ALLOWED_ORIGINS",
    "https://app.base44.com",
    "INVYRA_FORECASTING_SNAPSHOT_DIR",
    "INVYRA_FORECASTING_AUDIT_LOG_PATH",
    "INVYRA_FORECASTING_ACCURACY_LOG_PATH",
    "INVYRA_FORECASTING_REPORT_EXPORT_DIR",
    "mountPath: /var/data",
]

FORBIDDEN_MARKERS = [
    "value: *",
    "INVYRA_FORECASTING_ALLOWED_ORIGINS=*",
]


def main() -> None:
    if not BLUEPRINT.exists():
        raise SystemExit("Phase 2Q Render validation failed: render.yaml is missing.")

    content = BLUEPRINT.read_text(encoding="utf-8")
    for marker in REQUIRED_MARKERS:
        if marker not in content:
            raise SystemExit(f"Phase 2Q Render validation failed: missing marker {marker!r}.")

    for marker in FORBIDDEN_MARKERS:
        if marker in content:
            raise SystemExit(f"Phase 2Q Render validation failed: forbidden marker {marker!r}.")

    print("Phase 2Q Render blueprint validation passed.")


if __name__ == "__main__":
    main()
