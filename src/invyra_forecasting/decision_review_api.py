from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from invyra_forecasting.decision_review_dashboard import DecisionReviewDashboardProjection


@dataclass(frozen=True)
class DecisionReviewApiResponse:
    """Stable read-only API response shape for forecast review dashboards."""

    dashboard: DecisionReviewDashboardProjection
    response_version: str = "8H.1"
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "response_version": self.response_version,
            "dashboard": self.dashboard.to_dict(),
            "generated_at": self.generated_at,
            "advisory_only": True,
            "read_only": True,
            "inventory_source_of_truth_preserved": True,
        }


class DecisionReviewApiResponseBuilder:
    """Builds stable read-only API responses for future endpoint integration."""

    def build(self, dashboard: DecisionReviewDashboardProjection) -> DecisionReviewApiResponse:
        return DecisionReviewApiResponse(dashboard=dashboard)
