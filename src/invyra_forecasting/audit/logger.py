from typing import Any

from invyra_forecasting.constants import Environment
from invyra_forecasting.schemas import AuditEvent


def create_forecast_audit_event(actor: str, environment: Environment, item_id: str, location_id: str, details: dict[str, Any] | None = None) -> AuditEvent:
    return AuditEvent.create("FORECAST_CREATED", actor, environment, item_id, location_id, details)


def create_override_audit_event(actor: str, environment: Environment, item_id: str, location_id: str, original_recommendation: dict[str, Any], override_action: str, reason: str) -> AuditEvent:
    return AuditEvent.create(
        "FORECAST_RECOMMENDATION_OVERRIDDEN",
        actor,
        environment,
        item_id,
        location_id,
        {"original_recommendation": original_recommendation, "override_action": override_action, "reason": reason},
    )
