from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from invyra_forecasting.api.tenant_context import current_request_id, current_tenant_id

PRODUCTION_API_VERSION = "v1"
PRODUCTION_CONTRACT_VERSION = "1.0.0"
PRODUCTION_CONTRACT_STABILITY = "stable"


@dataclass(frozen=True)
class ProductionApiEnvelope:
    """Stable read-only response envelope for production API v1."""

    api_version: str
    resource: str
    data: Any
    advisory_only: bool = True
    read_only: bool = True
    inventory_source_of_truth_preserved: bool = True
    contract_version: str = PRODUCTION_CONTRACT_VERSION
    contract_stability: str = PRODUCTION_CONTRACT_STABILITY
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.api_version != PRODUCTION_API_VERSION:
            raise ValueError("only v1 production API responses are supported")
        if not self.resource:
            raise ValueError("resource is required")
        if not self.advisory_only:
            raise ValueError("production API responses must remain advisory-only")
        if not self.read_only:
            raise ValueError("production API responses must remain read-only")
        if not self.inventory_source_of_truth_preserved:
            raise ValueError("inventory source of truth must be preserved")
        if self.contract_version != PRODUCTION_CONTRACT_VERSION:
            raise ValueError("unsupported production API contract version")
        if self.contract_stability != PRODUCTION_CONTRACT_STABILITY:
            raise ValueError("production API contract must remain stable")

    def to_dict(self) -> dict[str, Any]:
        return {
            "api_version": self.api_version,
            "contract_version": self.contract_version,
            "contract_stability": self.contract_stability,
            "resource": self.resource,
            "data": self.data,
            "advisory_only": self.advisory_only,
            "read_only": self.read_only,
            "inventory_source_of_truth_preserved": self.inventory_source_of_truth_preserved,
            "metadata": dict(self.metadata),
        }


def production_envelope(resource: str, data: Any, **metadata: Any) -> dict[str, Any]:
    tenant_id = current_tenant_id()
    request_id = current_request_id()
    if tenant_id is not None:
        metadata.setdefault("tenant_id", tenant_id)
    if request_id is not None:
        metadata.setdefault("request_id", request_id)
    return ProductionApiEnvelope(api_version=PRODUCTION_API_VERSION, resource=resource, data=data, metadata=dict(metadata)).to_dict()


def paginated_envelope(
    resource: str,
    items: list[Any],
    *,
    limit: int,
    offset: int = 0,
    total: int | None = None,
    **metadata: Any,
) -> dict[str, Any]:
    if limit < 1:
        raise ValueError("limit must be at least 1")
    if offset < 0:
        raise ValueError("offset must be greater than or equal to 0")
    resolved_total = len(items) if total is None else total
    return production_envelope(
        resource,
        {
            "count": len(items),
            "items": items,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "total": resolved_total,
                "has_more": offset + len(items) < resolved_total,
            },
        },
        **metadata,
    )
