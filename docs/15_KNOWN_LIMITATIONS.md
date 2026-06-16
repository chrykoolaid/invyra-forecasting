# Known Limitations — Phase 1

Phase 1 is intentionally simple, explainable, and integration-ready. It is not the final enterprise production architecture.

## Persistence

- Snapshot, audit, and accuracy persistence currently use local files.
- There is no production database adapter yet.
- There are no retention policies yet.
- There are no signed audit exports yet.

## Forecasting Models

- Phase 1 uses explainable baseline forecasting.
- Advanced ML is not included yet.
- Seasonality is not fully modeled yet.
- Promotion, holiday, weather, expiry, supplier disruption, and event-driven demand effects are not active yet.

## Security and Permissions

- API authentication is not implemented yet.
- Role-based access control is not implemented yet.
- Manager override permission checks are not enforced in the engine yet.

## Integration

- The engine is not yet connected to the real Invyra Inventory ledger.
- The engine is not yet connected to the live Inventory UI.
- Dashboard, Reports, ScanOps, and Reorder Review contracts exist, but full module integration is still Phase 2+ work.

## Commercial Readiness

- Phase 1 is not a commercial deployment sign-off.
- Production hardening, monitoring, observability, database persistence, permissions, and deployment packaging are still required.

## Governance Reminder

Forecasting remains advisory and must not replace the inventory ledger, stock movements, manager approvals, or audit trail.
