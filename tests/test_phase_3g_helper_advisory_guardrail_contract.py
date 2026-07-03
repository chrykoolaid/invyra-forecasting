from pathlib import Path


def test_registry_helper_does_not_introduce_operational_write_paths():
    source = Path("src/invyra_forecasting/services/intelligence_forecasting.py").read_text()
    forbidden_terms = (
        "create_purchase_order",
        "approve_purchase_order",
        "StockMovement(",
        "append_movement",
        "mutate_inventory",
        "update_stock",
        "write_stock",
    )

    for term in forbidden_terms:
        assert term not in source


def test_registry_helper_keeps_forecast_service_call_as_advisory_context_passthrough():
    source = Path("src/invyra_forecasting/services/intelligence_forecasting.py").read_text()

    assert "intelligence_context=intelligence_context" in source
    assert "service.run_item_forecast" in source
    assert "write_snapshot=write_snapshot" in source
    assert "write_audit=write_audit" in source
