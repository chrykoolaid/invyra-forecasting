from dataclasses import dataclass
from datetime import date
from types import SimpleNamespace

from invyra_forecasting.constants import Environment
from invyra_forecasting.schemas import ExplanationResult
from invyra_forecasting.services.intelligence_forecasting import run_item_forecast_with_registry_intelligence
from invyra_forecasting.signals import InMemoryForecastSignalRegistry, make_location_stock_signal


@dataclass(frozen=True)
class _CapturedSnapshot:
    intelligence_context: dict
    explanation: ExplanationResult


class _ForecastingServiceSpy:
    def __init__(self) -> None:
        self.received_kwargs: dict = {}

    def run_item_forecast(self, bundle, **kwargs):
        self.received_kwargs = kwargs
        return _CapturedSnapshot(
            intelligence_context=kwargs["intelligence_context"],
            explanation=ExplanationResult(summary="Base summary", drivers=["Base driver"], warnings=[]),
        )


def _bundle():
    return SimpleNamespace(
        item=SimpleNamespace(item_id="ITEM-001"),
        location=SimpleNamespace(location_id="LOC-001"),
        environment=Environment.TEST,
    )


def test_helper_attaches_context_and_enriches_explanation():
    registry = InMemoryForecastSignalRegistry()
    registry.publish(
        make_location_stock_signal(
            item_id="ITEM-001",
            sku="SKU-1",
            location_id="LOC-001",
            on_hand=20,
            evidence_ref="SNAPSHOT-001",
            environment=Environment.TEST,
            confidence=0.8,
        )
    )
    service = _ForecastingServiceSpy()

    snapshot = run_item_forecast_with_registry_intelligence(
        service,
        _bundle(),
        registry,
        actor="test",
        anchor_date=date(2026, 7, 3),
    )

    assert snapshot.intelligence_context["item_id"] == "ITEM-001"
    assert snapshot.intelligence_context["location_id"] == "LOC-001"
    assert snapshot.intelligence_context["governance"]["advisory_only"] is True
    assert snapshot.explanation.summary == "Base summary"
    assert "Base driver" in snapshot.explanation.drivers
    assert any(driver.startswith("Forecast intelligence considered") for driver in snapshot.explanation.drivers)
    assert service.received_kwargs["actor"] == "test"
    assert service.received_kwargs["anchor_date"] == date(2026, 7, 3)
