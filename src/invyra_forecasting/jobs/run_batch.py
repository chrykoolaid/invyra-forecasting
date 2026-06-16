from invyra_forecasting.schemas import ForecastInputBundle
from invyra_forecasting.services import ForecastingService


def run_batch_job(bundles: list[ForecastInputBundle]) -> int:
    service = ForecastingService()
    snapshots = service.run_batch_forecast(bundles, actor="batch_job", write_snapshots=True)
    return len(snapshots)
