from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class DecisionReviewClientError(RuntimeError):
    """Raised when a read-only decision review client response is invalid."""


class SupportsDecisionReviewGet(Protocol):
    """Minimal HTTP client protocol required by the read-only reference client."""

    def get(self, path: str, **kwargs: Any) -> Any:
        """Return an HTTP response-like object with status_code and json()."""


@dataclass(frozen=True)
class DecisionReviewDashboardView:
    """Small downstream-friendly dashboard projection."""

    response_version: str
    total_count: int
    ready_count: int
    pending_count: int
    needs_more_evidence_count: int
    items: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class DecisionReviewExportBundleView:
    """Small downstream-friendly export bundle projection."""

    bundle_version: str
    export_version: str
    export_format: str
    ready_for_delivery: bool
    record_count: int
    valid: bool
    warnings: tuple[str, ...]


def assert_read_only_governance(payload: dict[str, Any]) -> None:
    """Validate advisory-only read-only governance flags on a response payload."""

    if payload.get("advisory_only") is not True:
        raise DecisionReviewClientError("Decision review payload is not marked advisory-only.")
    if payload.get("read_only") is not True:
        raise DecisionReviewClientError("Decision review payload is not marked read-only.")
    if payload.get("inventory_source_of_truth_preserved") is not True:
        raise DecisionReviewClientError("Decision review payload does not preserve Inventory as source of truth.")


def parse_dashboard_payload(payload: dict[str, Any]) -> DecisionReviewDashboardView:
    """Parse a dashboard response into a stable read-only consumer view."""

    assert_read_only_governance(payload)
    dashboard = _require_dict(payload, "dashboard")
    assert_read_only_governance(dashboard)
    summary = _require_dict(dashboard, "summary")
    snapshot = _require_dict(dashboard, "snapshot")

    return DecisionReviewDashboardView(
        response_version=_require_str(payload, "response_version"),
        total_count=_require_int(summary, "total_count"),
        ready_count=_require_int(summary, "ready_count"),
        pending_count=_require_int(summary, "pending_count"),
        needs_more_evidence_count=_require_int(summary, "needs_more_evidence_count"),
        items=tuple(_coerce_item(item) for item in _require_list(snapshot, "items")),
    )


def parse_export_bundle_payload(payload: dict[str, Any]) -> DecisionReviewExportBundleView:
    """Parse an export bundle response into a stable read-only consumer view."""

    assert_read_only_governance(payload)
    export = _require_dict(payload, "export")
    manifest = _require_dict(payload, "manifest")
    validation = _require_dict(payload, "validation")
    assert_read_only_governance(export)
    assert_read_only_governance(manifest)
    assert_read_only_governance(validation)

    return DecisionReviewExportBundleView(
        bundle_version=_require_str(payload, "bundle_version"),
        export_version=_require_str(export, "export_version"),
        export_format=_require_str(export, "export_format"),
        ready_for_delivery=_require_bool(payload, "ready_for_delivery"),
        record_count=_require_int(manifest, "record_count"),
        valid=_require_bool(validation, "valid"),
        warnings=tuple(str(warning) for warning in _require_list(validation, "warnings")),
    )


class DecisionReviewReferenceClient:
    """Read-only reference client for the Forecast Decision Review API."""

    def __init__(self, http_client: SupportsDecisionReviewGet) -> None:
        self._http_client = http_client

    def get_dashboard(self) -> DecisionReviewDashboardView:
        """Fetch and parse the read-only dashboard projection."""

        response = self._http_client.get("/forecast/decision-review/dashboard")
        return parse_dashboard_payload(_read_json_response(response, expected_status=200))

    def get_export_bundle(self, *, export_format: str = "json") -> DecisionReviewExportBundleView:
        """Fetch and parse the read-only export bundle projection."""

        response = self._http_client.get("/forecast/decision-review/export", params={"export_format": export_format})
        return parse_export_bundle_payload(_read_json_response(response, expected_status=200))


def _read_json_response(response: Any, *, expected_status: int) -> dict[str, Any]:
    status_code = getattr(response, "status_code", None)
    if status_code != expected_status:
        raise DecisionReviewClientError(f"Unexpected decision review response status: {status_code}")
    payload = response.json()
    if not isinstance(payload, dict):
        raise DecisionReviewClientError("Decision review response payload is not a dictionary.")
    return payload


def _require_dict(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise DecisionReviewClientError(f"Decision review field '{key}' is not a dictionary.")
    return value


def _require_list(payload: dict[str, Any], key: str) -> list[Any]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise DecisionReviewClientError(f"Decision review field '{key}' is not a list.")
    return value


def _require_str(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise DecisionReviewClientError(f"Decision review field '{key}' is not a string.")
    return value


def _require_bool(payload: dict[str, Any], key: str) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        raise DecisionReviewClientError(f"Decision review field '{key}' is not a boolean.")
    return value


def _require_int(payload: dict[str, Any], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int):
        raise DecisionReviewClientError(f"Decision review field '{key}' is not an integer.")
    return value


def _coerce_item(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise DecisionReviewClientError("Decision review queue item is not a dictionary.")
    return dict(value)
