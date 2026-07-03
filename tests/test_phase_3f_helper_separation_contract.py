from pathlib import Path


def test_base_forecasting_service_does_not_import_registry_helper():
    source = Path("src/invyra_forecasting/services/forecasting_service.py").read_text()

    assert "run_item_forecast_with_registry_intelligence" not in source
    assert "ForecastIntelligencePipeline" not in source
    assert "InMemoryForecastSignalRegistry" not in source


def test_registry_helper_remains_in_separate_service_module():
    source = Path("src/invyra_forecasting/services/intelligence_forecasting.py").read_text()

    assert "run_item_forecast_with_registry_intelligence" in source
    assert "ForecastingService" in source
    assert "ForecastIntelligencePipeline" in source
