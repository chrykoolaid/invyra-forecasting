from __future__ import annotations

from invyra_forecasting.models.contracts import ForecastModelInput, ForecastModelOutput


class BaselineExplainableDemandModel:
    """Simple explainable baseline model for Phase 2W.

    This is not an advanced ML model. It provides a deterministic advisory
    forecast from model-ready intelligence so future models can replace it
    without changing upstream signal or intelligence pipelines.
    """

    model_name = "baseline_explainable_demand_model"
    model_version = "2W.1"

    def forecast(self, model_input: ForecastModelInput, *, forecast_days: int = 30) -> ForecastModelOutput:
        average_daily_demand = max(model_input.average_daily_demand, 0.0)
        forecast_quantity = round(average_daily_demand * max(forecast_days, 0), 4)

        if model_input.latest_on_hand is None or average_daily_demand == 0:
            projected_days_of_cover = None
            stockout_risk = "UNKNOWN"
        else:
            projected_days_of_cover = round(model_input.latest_on_hand / average_daily_demand, 4)
            stockout_risk = self._risk_from_days_of_cover(projected_days_of_cover, forecast_days)

        explanation = self._build_explanation(
            model_input,
            forecast_days=forecast_days,
            forecast_quantity=forecast_quantity,
            projected_days_of_cover=projected_days_of_cover,
            stockout_risk=stockout_risk,
        )

        return ForecastModelOutput(
            item_id=model_input.item_id,
            location_id=model_input.location_id,
            environment=model_input.environment,
            forecast_days=forecast_days,
            forecast_quantity=forecast_quantity,
            projected_days_of_cover=projected_days_of_cover,
            stockout_risk=stockout_risk,
            confidence=model_input.confidence,
            explanation=explanation,
            evidence_refs=model_input.evidence_refs,
            model_name=self.model_name,
            model_version=self.model_version,
        )

    def _risk_from_days_of_cover(self, projected_days_of_cover: float, forecast_days: int) -> str:
        if projected_days_of_cover <= 3:
            return "HIGH"
        if projected_days_of_cover <= max(7, forecast_days * 0.35):
            return "MEDIUM"
        return "LOW"

    def _build_explanation(
        self,
        model_input: ForecastModelInput,
        *,
        forecast_days: int,
        forecast_quantity: float,
        projected_days_of_cover: float | None,
        stockout_risk: str,
    ) -> tuple[str, ...]:
        explanation = [
            f"Average daily demand from intelligence features is {model_input.average_daily_demand:.4f} units.",
            f"Projected demand over {forecast_days} days is {forecast_quantity:.4f} units.",
            f"Forecast confidence is {model_input.confidence:.4f} based on signal quality and weighting.",
            f"Stockout risk is {stockout_risk}.",
        ]
        if projected_days_of_cover is None:
            explanation.append("Days of cover is unknown because on-hand stock or demand evidence is unavailable.")
        else:
            explanation.append(f"Projected days of cover is {projected_days_of_cover:.4f} days.")
        if model_input.evidence_refs:
            explanation.append(f"Forecast is linked to {len(model_input.evidence_refs)} evidence reference(s).")
        else:
            explanation.append("Forecast has no evidence references and should be treated with caution.")
        return tuple(explanation)
