def test_registry_helper_import_paths_remain_compatible():
    from invyra_forecasting.services import run_item_forecast_with_registry_intelligence as package_helper
    from invyra_forecasting.services.intelligence_forecasting import (
        run_item_forecast_with_registry_intelligence as direct_helper,
    )

    assert package_helper is direct_helper


def test_base_forecasting_service_import_paths_remain_compatible():
    from invyra_forecasting.services import ForecastingService as package_service
    from invyra_forecasting.services.forecasting_service import ForecastingService as direct_service

    assert package_service is direct_service
