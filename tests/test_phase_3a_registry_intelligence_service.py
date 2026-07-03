from dataclasses import dataclass
from datetime import date
from types import SimpleNamespace

from invyra_forecasting.constants import Environment
from invyra_forecasting.services.intelligence_forecasting import run_item_forecast_with_registry_intelligence
from invyra_forecasting.signals import InMemoryForecastSignalRegistry, make_location_stock_signal


@dataclass(frozen=True)
class _CapturedSnapshot:
    intelligence_context: dict


class _ForecastingServiceSpy:
    def __init__(self) -> None:
        self.received_kwargs: dict = {}

    def run_item_forecast(self, bundle, **kwargs):
        self.received_kwargs = kwargs
        return _CapturedSnapshot(intelligence_context=kwargs["intelligence_context"])


def _bundle():
    return SimpleNamespace(
        item=SimpleNamespace(item_id="ITEM-001"),
        location=SimpleNamespace(location_id="LOC-001"),
        environment=Environment.TEST,
    )


def test_registry_intelligence_helper_attaches_context_metadata():
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

    context = snapshot.intelligence_context
    assert context["item_id"] == "ITEM-001"
    assert context["location_id"] == "LOC-001"
    assert context["signal_count"] == 1
    assert context["feature_summary"]["latest_on_hand"] == 20
    assert context["governance"]["advisory_only"] is True
    assert service.received_kwargs["actor"] == "test"
    assert service.received_kwargs["anchor_date"] == date(2026, 7, 3)
