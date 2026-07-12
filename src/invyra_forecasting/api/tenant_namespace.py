from __future__ import annotations

from invyra_forecasting.api.tenant_context import current_tenant_id, normalize_tenant_id

DEFAULT_NAMESPACE = "default"


def normalize_namespace(raw: str | None) -> str:
    """Return the internal namespace for an optional tenant identifier."""

    return normalize_tenant_id(raw) or DEFAULT_NAMESPACE


def current_namespace() -> str:
    """Return the namespace bound to the current request context."""

    return normalize_namespace(current_tenant_id())
