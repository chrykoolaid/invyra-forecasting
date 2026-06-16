from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class EndpointContract:
    method: str
    route: str
    purpose: str
    request_contract: str
    response_keys: list[str]
    governance_rules: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ModuleIntegrationContract:
    module_name: str
    status: str
    source_of_truth: str
    endpoints: list[EndpointContract]
    must_send: list[str]
    must_receive: list[str]
    must_not_do: list[str]
    fallback_behavior: list[str]
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
