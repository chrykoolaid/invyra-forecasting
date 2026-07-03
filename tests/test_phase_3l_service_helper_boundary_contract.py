from pathlib import Path


def test_services_package_exports_helper_without_moving_implementation():
    services_init = Path("src/invyra_forecasting/services/__init__.py").read_text()
    helper_source = Path("src/invyra_forecasting/services/intelligence_forecasting.py").read_text()

    assert "run_item_forecast_with_registry_intelligence" in services_init
    assert "def run_item_forecast_with_registry_intelligence" in helper_source


def test_base_forecasting_service_keeps_registry_helper_out_of_core_module():
    source = Path("src/invyra_forecasting/services/forecasting_service.py").read_text()

    assert "run_item_forecast_with_registry_intelligence" not in source
    assert "ForecastIntelligencePipeline" not in source
    assert "InMemoryForecastSignalRegistry" not in source


def test_registry_helper_still_uses_forecasting_service_boundary():
    source = Path("src/invyra_forecasting/services/intelligence_forecasting.py").read_text()

    assert "service.run_item_forecast" in source
    assert "intelligence_context=intelligence_context" in source
    assert "write_snapshot=write_snapshot" in source
    assert "write_audit=write_audit" in source
