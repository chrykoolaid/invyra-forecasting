from __future__ import annotations

from invyra_forecasting.integrations.contracts import EndpointContract, ModuleIntegrationContract

_ADVISORY = "Forecasting output is advisory and must not mutate inventory, purchasing, or stock ledger records."
_ENVIRONMENT = "Payloads and responses must preserve LIVE / TRAINING / TEST environment separation."
_NO_AUTO_PURCHASE = "Recommendations must not automatically create or approve purchase orders."


def _endpoint(method: str, route: str, purpose: str, request_contract: str, response_keys: list[str], extra_rules: list[str] | None = None) -> EndpointContract:
    return EndpointContract(
        method=method,
        route=route,
        purpose=purpose,
        request_contract=request_contract,
        response_keys=response_keys,
        governance_rules=[_ADVISORY, _ENVIRONMENT] + (extra_rules or []),
    )


CONTRACTS: dict[str, ModuleIntegrationContract] = {
    "inventory": ModuleIntegrationContract(
        module_name="inventory",
        status="Phase 1H locked contract",
        source_of_truth="Inventory ledger remains source of truth for stock on hand and movements.",
        endpoints=[
            _endpoint("POST", "/forecasts/item", "Item Details forecast and risk panel", "ForecastRequest", ["forecast", "risk", "recommendation", "confidence", "explanation", "audit_event"]),
            _endpoint("GET", "/snapshots/{snapshot_id}", "Read back forecast evidence for item-level drill-down", "snapshot_id", ["snapshot_id", "forecast", "risk", "recommendation", "confidence"]),
        ],
        must_send=["item", "location", "stock_position", "movements", "supplier_profile", "environment"],
        must_receive=["forecast_quantity", "days_of_cover", "stockout_risk", "overstock_risk", "confidence", "explanation"],
        must_not_do=["Treat forecast as stock truth", "Hide low-confidence warning", "Mutate stock from forecast output"],
        fallback_behavior=["Show forecast unavailable state", "Keep existing inventory item details usable", "Prompt user to verify movement history when confidence is low"],
        notes=["Item Details should display forecast as an intelligence panel, not a replacement for stock history."],
    ),
    "scanops": ModuleIntegrationContract(
        module_name="scanops",
        status="Phase 1H locked contract",
        source_of_truth="ScanOps captures observations; Inventory ledger remains stock truth.",
        endpoints=[
            _endpoint("POST", "/risk/stockout", "Gap Scan and Floor Scan risk interpretation", "ForecastRequest", ["risk", "confidence", "explanation"]),
        ],
        must_send=["item", "location", "stock_position", "movements", "supplier_profile", "environment"],
        must_receive=["stockout_risk", "days_of_cover", "confidence", "warnings"],
        must_not_do=["Treat scan observation as forecast truth", "Auto-adjust stock from risk output", "Suppress low-confidence scan warnings"],
        fallback_behavior=["Continue manual scan validation", "Show risk unavailable state", "Allow supervisor review"],
        notes=["ScanOps should use forecasting to prioritize attention, not to bypass variance investigation."],
    ),
    "reorder_review": ModuleIntegrationContract(
        module_name="reorder_review",
        status="Phase 1H locked contract",
        source_of_truth="Reorder Review owns approval workflow; forecasting provides advisory quantities only.",
        endpoints=[
            _endpoint("POST", "/recommendations/reorder", "Suggested quantity, urgency, risk, confidence, and reason", "ForecastRequest", ["recommendation", "risk", "confidence", "explanation"], [_NO_AUTO_PURCHASE]),
        ],
        must_send=["item", "location", "stock_position", "movements", "supplier_profile", "environment"],
        must_receive=["suggested_reorder_quantity", "urgency", "stockout_risk", "confidence", "explanation"],
        must_not_do=["Auto-approve recommendation", "Create PO without user action", "Hide recommendation reason"],
        fallback_behavior=["Allow manual reorder review", "Show recommendation unavailable", "Require manager review for low confidence"],
        notes=["Recommendations should be displayed with reasons and confidence chips."],
    ),
    "dashboard": ModuleIntegrationContract(
        module_name="dashboard",
        status="Phase 1H locked contract",
        source_of_truth="Dashboard summarizes persisted evidence; it does not create forecast records by itself.",
        endpoints=[
            _endpoint("POST", "/forecasts/batch", "Batch forecast for risk summaries", "BatchForecastRequest", ["count", "snapshots"]),
        ],
        must_send=["requests", "environment"],
        must_receive=["snapshot_count", "stockout_risk_counts", "overstock_risk_counts", "confidence_rating_counts"],
        must_not_do=["Replace existing priority issue logic", "Hide missing forecast data", "Block dashboard when forecasting is unavailable"],
        fallback_behavior=["Use existing Priority Inventory Issues fallback", "Show forecasting unavailable notice", "Keep dashboard loadable"],
        notes=["Dashboard should summarize forecasting intelligence without making the home screen noisy."],
    ),
    "reports": ModuleIntegrationContract(
        module_name="reports",
        status="Phase 1H locked contract",
        source_of_truth="Reports read persisted forecast evidence and exports only.",
        endpoints=[
            _endpoint("GET", "/reports/summary", "Management summary for forecast outputs", "query filters", ["snapshot_count", "accuracy_count", "audit_event_count", "average_accuracy_score"]),
        ],
        must_send=["environment filter", "optional item/location filters", "limit"],
        must_receive=["summary counts", "risk counts", "accuracy metrics", "audit counts"],
        must_not_do=["Treat exports as ledger", "Alter audit or forecast records", "Hide low-confidence forecasts"],
        fallback_behavior=["Show empty report state", "Allow CSV/JSON export retry", "Display missing evidence notice"],
        notes=["Reports should make forecast evidence reviewable for managers and future audits."],
    ),
}


def list_module_contracts() -> list[dict]:
    return [CONTRACTS[key].to_dict() for key in sorted(CONTRACTS)]


def get_module_contract(module_name: str) -> ModuleIntegrationContract:
    key = module_name.strip().lower().replace("-", "_").replace(" ", "_")
    if key not in CONTRACTS:
        raise KeyError(f"Unknown module contract: {module_name}")
    return CONTRACTS[key]


def validate_module_contract(contract: ModuleIntegrationContract) -> list[str]:
    errors: list[str] = []
    if not contract.module_name:
        errors.append("module_name is required")
    if not contract.endpoints:
        errors.append(f"{contract.module_name}: at least one endpoint is required")
    if not any("environment" in item.lower() for item in contract.must_send):
        errors.append(f"{contract.module_name}: must_send must include environment")
    if not contract.must_receive:
        errors.append(f"{contract.module_name}: must_receive is required")
    for endpoint in contract.endpoints:
        if endpoint.method not in {"GET", "POST"}:
            errors.append(f"{contract.module_name}: unsupported method {endpoint.method}")
        if not endpoint.route.startswith("/"):
            errors.append(f"{contract.module_name}: endpoint route must start with slash")
        if not endpoint.response_keys:
            errors.append(f"{contract.module_name}: endpoint response_keys are required")
    return errors
