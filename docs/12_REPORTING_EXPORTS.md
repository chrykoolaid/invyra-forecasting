# Reporting and Export Foundation — Phase 1G

Phase 1G adds read-only report summaries and export-ready files for the forecasting engine.

## Report Sources

- Forecast snapshots from `data/snapshots/*.json`
- Audit events from `data/snapshots/audit_events.jsonl`
- Accuracy events from `data/snapshots/accuracy_events.jsonl`
- Confidence notes embedded in forecast snapshots

## Report Types

```text
summary
snapshots
accuracy
audit
confidence
```

## Export Formats

```text
json
csv
```

## Export Location

Reports are written to `data/reports/` by default.

The default export directory can be changed with `INVYRA_REPORT_EXPORT_DIR`.

## Governance Rules

- Reports are generated from persisted evidence only.
- Reports are read-only.
- Reports preserve environment separation.
- Reports must not hide low-confidence forecasts.
- Exports are operational aids, not the inventory ledger.
