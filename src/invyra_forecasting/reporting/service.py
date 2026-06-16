from __future__ import annotations

import csv
import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from invyra_forecasting.accuracy import JsonlAccuracyStore
from invyra_forecasting.audit import JsonlAuditStore
from invyra_forecasting.config import ForecastingConfig
from invyra_forecasting.data.repositories import FileSnapshotRepository
from invyra_forecasting.reporting.entities import ReportExportResult


class ReportService:
    """Builds read-only report summaries and JSON/CSV exports."""

    VALID_REPORT_TYPES = {"summary", "snapshots", "accuracy", "audit", "confidence"}
    VALID_FORMATS = {"json", "csv"}

    def __init__(self, config: ForecastingConfig | None = None) -> None:
        self.config = config or ForecastingConfig.from_env()
        self.snapshot_repository = FileSnapshotRepository(self.config.snapshot_dir)
        self.audit_store = JsonlAuditStore(self.config.audit_log_path)
        self.accuracy_store = JsonlAccuracyStore(self.config.accuracy_log_path)
        self.report_export_dir = Path(self.config.report_export_dir)

    def build_summary(self, item_id: str | None = None, location_id: str | None = None, environment: str | None = None, limit: int = 100) -> dict[str, Any]:
        snapshots = self.snapshot_rows(item_id=item_id, location_id=location_id, environment=environment, limit=limit)
        accuracy = self.accuracy_rows(item_id=item_id, location_id=location_id, environment=environment, limit=limit)
        audit = self.audit_rows(item_id=item_id, location_id=location_id, environment=environment, limit=limit)
        confidence = self.confidence_rows(item_id=item_id, location_id=location_id, environment=environment, limit=limit)
        accuracy_scores = [float(row["accuracy_score"]) for row in accuracy if row.get("accuracy_score") is not None]
        average_accuracy = None if not accuracy_scores else round(sum(accuracy_scores) / len(accuracy_scores), 4)
        return {
            "generated_at_utc": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "filters": self._filters(item_id, location_id, environment, limit),
            "snapshot_count": len(snapshots),
            "accuracy_count": len(accuracy),
            "audit_event_count": len(audit),
            "confidence_note_count": len(confidence),
            "average_accuracy_score": average_accuracy,
            "stockout_risk_counts": self._count_by_key(snapshots, "stockout_risk"),
            "overstock_risk_counts": self._count_by_key(snapshots, "overstock_risk"),
            "audit_event_counts": self._count_by_key(audit, "event_type"),
            "confidence_rating_counts": self._count_by_key(confidence, "confidence_rating"),
            "recalibrated_confidence_count": sum(1 for row in confidence if row.get("accuracy_recalibrated")),
        }

    def export_report(self, report_type: str, export_format: str, item_id: str | None = None, location_id: str | None = None, environment: str | None = None, limit: int = 100) -> ReportExportResult:
        report_type = report_type.lower()
        export_format = export_format.lower()
        if report_type not in self.VALID_REPORT_TYPES:
            raise ValueError(f"Unsupported report_type: {report_type}")
        if export_format not in self.VALID_FORMATS:
            raise ValueError(f"Unsupported export_format: {export_format}")
        data = self._data_for_report(report_type, item_id, location_id, environment, limit)
        rows = data if isinstance(data, list) else [data]
        self.report_export_dir.mkdir(parents=True, exist_ok=True)
        path = self.report_export_dir / self._filename(report_type, export_format)
        if export_format == "json":
            path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        else:
            self._write_csv(path, rows)
        return ReportExportResult.create(report_type, export_format, str(path), len(rows), self._filters(item_id, location_id, environment, limit))

    def snapshot_rows(self, item_id: str | None = None, location_id: str | None = None, environment: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for snapshot_id in self.snapshot_repository.list_snapshot_ids():
            snapshot = self.snapshot_repository.get(snapshot_id)
            if not snapshot:
                continue
            forecast = snapshot.get("forecast", {})
            risk = snapshot.get("risk", {})
            recommendation = snapshot.get("recommendation", {})
            confidence = snapshot.get("confidence", {})
            row = {
                "snapshot_id": snapshot.get("snapshot_id"),
                "item_id": forecast.get("item_id"),
                "location_id": forecast.get("location_id"),
                "environment": forecast.get("environment"),
                "forecast_quantity": forecast.get("forecast_quantity"),
                "average_daily_demand": forecast.get("average_daily_demand"),
                "stockout_risk": risk.get("stockout_risk"),
                "overstock_risk": risk.get("overstock_risk"),
                "suggested_reorder_quantity": recommendation.get("suggested_reorder_quantity"),
                "confidence_rating": confidence.get("rating"),
                "confidence_score": confidence.get("score"),
            }
            if self._row_matches(row, item_id, location_id, environment):
                rows.append(row)
        return rows[-max(1, limit):]

    def accuracy_rows(self, item_id: str | None = None, location_id: str | None = None, environment: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        return self.accuracy_store.list_results(limit=limit, item_id=item_id, location_id=location_id, environment=environment)

    def audit_rows(self, item_id: str | None = None, location_id: str | None = None, environment: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        return self.audit_store.list_events(limit=limit, item_id=item_id, location_id=location_id, environment=environment)

    def confidence_rows(self, item_id: str | None = None, location_id: str | None = None, environment: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for snapshot_id in self.snapshot_repository.list_snapshot_ids():
            snapshot = self.snapshot_repository.get(snapshot_id)
            if not snapshot:
                continue
            forecast = snapshot.get("forecast", {})
            confidence = snapshot.get("confidence", {})
            reasons = confidence.get("reasons", []) or []
            row = {
                "snapshot_id": snapshot.get("snapshot_id"),
                "item_id": forecast.get("item_id"),
                "location_id": forecast.get("location_id"),
                "environment": forecast.get("environment"),
                "confidence_rating": confidence.get("rating"),
                "confidence_score": confidence.get("score"),
                "accuracy_recalibrated": any("Accuracy recalibration" in str(reason) for reason in reasons),
                "confidence_reasons": " | ".join(str(reason) for reason in reasons),
            }
            if self._row_matches(row, item_id, location_id, environment):
                rows.append(row)
        return rows[-max(1, limit):]

    def _data_for_report(self, report_type: str, item_id: str | None, location_id: str | None, environment: str | None, limit: int) -> dict[str, Any] | list[dict[str, Any]]:
        if report_type == "summary":
            return self.build_summary(item_id, location_id, environment, limit)
        if report_type == "snapshots":
            return self.snapshot_rows(item_id, location_id, environment, limit)
        if report_type == "accuracy":
            return self.accuracy_rows(item_id, location_id, environment, limit)
        if report_type == "audit":
            return self.audit_rows(item_id, location_id, environment, limit)
        return self.confidence_rows(item_id, location_id, environment, limit)

    def _write_csv(self, path: Path, rows: list[dict[str, Any]]) -> None:
        fieldnames = sorted({key for row in rows for key in row.keys()}) if rows else []
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            if fieldnames:
                writer.writeheader()
                for row in rows:
                    writer.writerow({key: self._csv_value(row.get(key)) for key in fieldnames})

    def _csv_value(self, value: Any) -> Any:
        if isinstance(value, (dict, list)):
            return json.dumps(value, default=str)
        return value

    def _filename(self, report_type: str, export_format: str) -> str:
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        return f"invyra_forecast_{report_type}_{stamp}.{export_format}"

    def _filters(self, item_id: str | None, location_id: str | None, environment: str | None, limit: int) -> dict[str, Any]:
        return {"item_id": item_id, "location_id": location_id, "environment": environment, "limit": limit}

    def _row_matches(self, row: dict[str, Any], item_id: str | None, location_id: str | None, environment: str | None) -> bool:
        if item_id and row.get("item_id") != item_id:
            return False
        if location_id and row.get("location_id") != location_id:
            return False
        if environment and row.get("environment") != environment:
            return False
        return True

    def _count_by_key(self, rows: list[dict[str, Any]], key: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        for row in rows:
            value = row.get(key)
            if value is None:
                continue
            counts[str(value)] = counts.get(str(value), 0) + 1
        return counts
