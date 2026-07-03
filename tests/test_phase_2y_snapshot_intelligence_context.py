from invyra_forecasting.constants import Environment
from invyra_forecasting.schemas import (
    AuditEvent,
    ConfidenceResult,
    ExplanationResult,
    ForecastResult,
    ForecastSnapshot,
    RecommendationResult,
    RiskResult,
)


def _snapshot(intelligence_context=None):
    return ForecastSnapshot.create(
        input_summary={"item_id": "ITEM-001", "location_id": "LOC-001"},
        forecast=ForecastResult(
            item_id="ITEM-001",
            location_id="LOC-001",
            forecast_horizon_days=14,
            forecast_quantity=10,
            average_daily_demand=1.5,
            method="simple_average",
            environment=Environment.TEST,
        ),
        risk=RiskResult(
            item_id="ITEM-001",
            location_id="LOC-001",
            days_of_cover=5,
            stockout_risk="LOW",
            overstock_risk="LOW",
            estimated_stockout_date=None,
            environment=Environment.TEST,
        ),
        recommendation=RecommendationResult(
            item_id="ITEM-001",
            location_id="LOC-001",
            reorder_needed=False,
            suggested_reorder_quantity=0,
            urgency="LOW",
            supplier_lead_time_days=3,
            environment=Environment.TEST,
        ),
        confidence=ConfidenceResult(rating="HIGH", score=0.9),
        explanation=ExplanationResult(summary="Stable demand"),
        audit_event=AuditEvent.create(
            event_type="FORECAST_CREATED",
            actor="test",
            environment=Environment.TEST,
            item_id="ITEM-001",
            location_id="LOC-001",
        ),
        intelligence_context=intelligence_context,
    )


def test_snapshot_supports_optional_intelligence_context():
    snapshot = _snapshot(
        {
            "signal_count": 2,
            "confidence": 0.75,
            "governance": {"advisory_only": True, "source_of_truth_preserved": True},
        }
    )

    payload = snapshot.to_dict()

    assert payload["intelligence_context"]["signal_count"] == 2
    assert payload["intelligence_context"]["governance"]["advisory_only"] is True
    assert snapshot.recommendation.suggested_reorder_quantity == 0


def test_snapshot_context_defaults_to_none_for_existing_callers():
    snapshot = _snapshot()

    assert snapshot.intelligence_context is None
    assert snapshot.to_dict()["intelligence_context"] is None
