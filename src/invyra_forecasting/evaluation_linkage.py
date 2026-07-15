from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable

from invyra_forecasting.api.tenant_namespace import current_namespace
from invyra_forecasting.evaluation.persistence import ForecastEvaluationRecord
from invyra_forecasting.history import ForecastHistoryRecord


@dataclass(frozen=True)
class ForecastEvaluationLink:
    """Immutable identity link between forecast history and evaluation evidence."""

    link_id: str
    evaluation_id: str
    history_id: str
    forecast_id: str
    snapshot_id: str | None
    item_id: str
    location_id: str
    model_name: str
    model_version: str
    forecast_horizon_days: int
    history_version_number: int
    advisory_only: bool = True
    read_only: bool = True
    inventory_source_of_truth_preserved: bool = True

    def __post_init__(self) -> None:
        required = {
            "link_id": self.link_id,
            "evaluation_id": self.evaluation_id,
            "history_id": self.history_id,
            "forecast_id": self.forecast_id,
            "item_id": self.item_id,
            "location_id": self.location_id,
            "model_name": self.model_name,
            "model_version": self.model_version,
        }
        for field_name, value in required.items():
            if not value:
                raise ValueError(f"{field_name} is required")
        if self.forecast_horizon_days < 1:
            raise ValueError("forecast_horizon_days must be 1 or greater")
        if self.history_version_number < 1:
            raise ValueError("history_version_number must be 1 or greater")
        if not self.advisory_only:
            raise ValueError("evaluation links must remain advisory-only")
        if not self.read_only:
            raise ValueError("evaluation links must remain read-only")
        if not self.inventory_source_of_truth_preserved:
            raise ValueError("inventory source of truth must be preserved")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class InMemoryForecastEvaluationLinkRepository:
    """Tenant-isolated, append-only storage for immutable evaluation links."""

    def __init__(self, links: Iterable[ForecastEvaluationLink] = ()) -> None:
        self._links_by_namespace: dict[str, dict[str, ForecastEvaluationLink]] = {}
        for link in links:
            self.append(link)

    def _links(self) -> dict[str, ForecastEvaluationLink]:
        return self._links_by_namespace.setdefault(current_namespace(), {})

    def append(self, link: ForecastEvaluationLink) -> ForecastEvaluationLink:
        links = self._links()
        if link.link_id in links:
            raise ValueError(f"evaluation link already exists: {link.link_id}")
        if any(existing.evaluation_id == link.evaluation_id for existing in links.values()):
            raise ValueError(f"evaluation already linked: {link.evaluation_id}")
        links[link.link_id] = link
        return link

    def get(self, link_id: str) -> ForecastEvaluationLink | None:
        return self._links().get(link_id)

    def for_evaluation(self, evaluation_id: str) -> ForecastEvaluationLink | None:
        return next(
            (link for link in self._links().values() if link.evaluation_id == evaluation_id),
            None,
        )

    def for_history(self, history_id: str) -> tuple[ForecastEvaluationLink, ...]:
        return tuple(
            sorted(
                (link for link in self._links().values() if link.history_id == history_id),
                key=lambda link: (link.evaluation_id, link.link_id),
            )
        )


class ForecastEvaluationLinkageService:
    def __init__(self, repository: InMemoryForecastEvaluationLinkRepository | None = None) -> None:
        self._repository = repository or InMemoryForecastEvaluationLinkRepository()

    def link(
        self,
        history: ForecastHistoryRecord,
        evaluation: ForecastEvaluationRecord,
        *,
        link_id: str | None = None,
    ) -> ForecastEvaluationLink:
        self._validate_identity(history, evaluation)
        horizon = evaluation.result.evaluation_metadata.get("forecast_horizon_days")
        if not isinstance(horizon, int) or isinstance(horizon, bool) or horizon < 1:
            raise ValueError("evaluation must contain a valid forecast_horizon_days value")
        resolved_snapshot_id = evaluation.snapshot_id or history.snapshot_id
        link = ForecastEvaluationLink(
            link_id=link_id or evaluation.evaluation_id,
            evaluation_id=evaluation.evaluation_id,
            history_id=history.history_id,
            forecast_id=history.forecast_id,
            snapshot_id=resolved_snapshot_id,
            item_id=history.item_id,
            location_id=history.location_id,
            model_name=history.model_name,
            model_version=history.model_version,
            forecast_horizon_days=horizon,
            history_version_number=history.version_number,
        )
        return self._repository.append(link)

    def get(self, link_id: str) -> ForecastEvaluationLink | None:
        return self._repository.get(link_id)

    def for_evaluation(self, evaluation_id: str) -> ForecastEvaluationLink | None:
        return self._repository.for_evaluation(evaluation_id)

    def for_history(self, history_id: str) -> tuple[ForecastEvaluationLink, ...]:
        return self._repository.for_history(history_id)

    @staticmethod
    def _validate_identity(
        history: ForecastHistoryRecord,
        evaluation: ForecastEvaluationRecord,
    ) -> None:
        comparisons = {
            "forecast_id": (history.forecast_id, evaluation.forecast_id),
            "item_id": (history.item_id, evaluation.item_id),
            "location_id": (history.location_id, evaluation.location_id),
            "model_name": (history.model_name, evaluation.model_name),
            "model_version": (history.model_version, evaluation.model_version),
        }
        for field_name, (history_value, evaluation_value) in comparisons.items():
            if history_value != evaluation_value:
                raise ValueError(f"history and evaluation {field_name} must match")
        if (
            history.snapshot_id is not None
            and evaluation.snapshot_id is not None
            and history.snapshot_id != evaluation.snapshot_id
        ):
            raise ValueError("history and evaluation snapshot_id must match when both are present")
        if not history.advisory_only or not evaluation.advisory_only:
            raise ValueError("linked records must remain advisory-only")
        if not history.read_only or not evaluation.read_only:
            raise ValueError("linked records must remain read-only")
        if (
            not history.inventory_source_of_truth_preserved
            or not evaluation.inventory_source_of_truth_preserved
        ):
            raise ValueError("inventory source of truth must be preserved")
