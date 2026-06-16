# Integration Readiness Matrix — Phase 1

| Module | Contract Status | Ready For | Not Yet Ready For | Notes |
|---|---|---|---|---|
| Inventory | Locked Phase 1H contract | Phase 2 Item Details forecast panel planning | Direct live ledger integration | Inventory remains source of truth. |
| ScanOps | Locked Phase 1H contract | Gap Scan / Floor Scan risk interpretation planning | Automatic stock adjustment | Forecast risk must not bypass variance review. |
| Reorder Review | Locked Phase 1H contract | Advisory quantity, urgency, reason, confidence | Auto-approval or auto-PO creation | Manager/user review remains required. |
| Dashboard | Locked Phase 1H contract | Forecast risk summary planning | Replacing existing Priority Inventory Issues logic | Dashboard fallback must remain. |
| Reports | Locked Phase 1H contract | Forecast evidence summaries and exports | Treating exports as ledger truth | Reports are read-only evidence. |
| Purchasing | Partial via Reorder Review contract | Draft PO advisory support planning | Automatic purchasing | Phase 2/3 hardening required. |
| Suppliers | Partial lead-time input support | Supplier lead-time impact planning | Supplier reliability scoring as final production signal | Supplier reliability is future work. |
| Markdowns | Future placeholder | Future expiry/markdown pressure planning | Active markdown automation | Out of Phase 1 scope. |
| Wastage | Partial movement signal support | Wastage as demand signal where valid | Full wastage forecasting | Future wastage pressure model required. |
| POS | Partial sales signal support | POS sale movements as demand input | POS-side forecasting UI | POS remains transaction source. |
| CRM | Future placeholder | Future customer demand planning | Customer-level prediction | Out of Phase 1 scope. |

## Readiness Summary

Phase 1 is ready for controlled Phase 2 integration planning with Inventory as the first implementation target.

The correct next integration order is:

1. Inventory Item Details forecast panel
2. Reorder Review advisory recommendation wiring
3. Dashboard read-only summary surface
4. Reports evidence export surface
5. ScanOps risk interpretation support

This order keeps daily workflows clean and avoids overloading staff screens.
