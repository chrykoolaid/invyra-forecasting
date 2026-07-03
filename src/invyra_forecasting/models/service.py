from __future__ import annotations

from invyra_forecasting.intelligence.objects import ForecastIntelligence
from invyra_forecasting.models.baseline import BaselineExplainableDemandModel
from invyra_forecasting.models.contracts import ForecastModelOutput
from invyra_forecasting.models.handoff import ForecastModelHandoffAdapter


class ForecastModelService:
    """Runs advisory forecast models from ForecastIntelligence inputs."""

    def __init__(
        self,
        *,
        handoff_adapter: ForecastModelHandoffAdapter | None = None,
        baseline_model: BaselineExplainableDemandModel | None = None,
    ) -> None:
        self._handoff_adapter = handoff_adapter or ForecastModelHandoffAdapter()
        self._baseline_model = baseline_model or BaselineExplainableDemandModel()

    def forecast(self, intelligence: ForecastIntelligence, *, forecast_days: int = 30) -> ForecastModelOutput:
        model_input = self._handoff_adapter.from_intelligence(intelligence)
        return self._baseline_model.forecast(model_input, forecast_days=forecast_days)
