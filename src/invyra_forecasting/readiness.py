from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any, Iterable


class ReadinessStatus(StrEnum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


@dataclass(frozen=True)
class ReadinessCheck:
    check_id: str
    category: str
    status: ReadinessStatus
    message: str
    evidence: tuple[str, ...] = ()
    advisory_only: bool = True
    read_only: bool = True
    inventory_source_of_truth_preserved: bool = True

    def __post_init__(self) -> None:
        if not self.check_id:
            raise ValueError("check_id is required")
        if not self.category:
            raise ValueError("category is required")
        if not self.message:
            raise ValueError("message is required")
        if not self.advisory_only:
            raise ValueError("readiness checks must remain advisory-only")
        if not self.read_only:
            raise ValueError("readiness checks must remain read-only")
        if not self.inventory_source_of_truth_preserved:
            raise ValueError("inventory source of truth must be preserved")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["status"] = self.status.value
        payload["evidence"] = list(self.evidence)
        return payload


@dataclass(frozen=True)
class EnterpriseReadinessReport:
    status: ReadinessStatus
    checks: tuple[ReadinessCheck, ...]
    pass_count: int
    warn_count: int
    fail_count: int
    summary: str
    advisory_only: bool = True
    read_only: bool = True
    inventory_source_of_truth_preserved: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.advisory_only:
            raise ValueError("readiness reports must remain advisory-only")
        if not self.read_only:
            raise ValueError("readiness reports must remain read-only")
        if not self.inventory_source_of_truth_preserved:
            raise ValueError("inventory source of truth must be preserved")

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "checks": [check.to_dict() for check in self.checks],
            "pass_count": self.pass_count,
            "warn_count": self.warn_count,
            "fail_count": self.fail_count,
            "summary": self.summary,
            "advisory_only": self.advisory_only,
            "read_only": self.read_only,
            "inventory_source_of_truth_preserved": self.inventory_source_of_truth_preserved,
            "metadata": dict(self.metadata),
        }


class EnterpriseReadinessAuditService:
    REQUIRED_V1_ENDPOINTS = (
        "/v1/forecasts/item",
        "/v1/snapshots/{snapshot_id}",
        "/v1/evaluations/accuracy/item/{item_id}",
        "/v1/models/registry",
        "/v1/models/capabilities",
        "/v1/monitoring/summary",
        "/v1/performance/summary",
        "/v1/hardening/summary",
    )

    REQUIRED_CAPABILITIES = (
        "performance_aware_model_selection",
        "evaluation_persistence",
        "model_registry_v2",
        "drift_detection",
        "evidence_scoring_v2",
        "production_apis",
        "forecast_monitoring",
        "performance_observability",
        "production_hardening",
    )

    def audit(
        self,
        *,
        stable_resources: Iterable[str],
        capabilities: Iterable[str] | None = None,
        ci_passed: bool = True,
        api_read_only: bool = True,
        governance_flags_present: bool = True,
    ) -> EnterpriseReadinessReport:
        resources = tuple(stable_resources)
        capability_set = tuple(capabilities or self.REQUIRED_CAPABILITIES)
        checks = (
            self._governance_check(api_read_only=api_read_only, governance_flags_present=governance_flags_present),
            self._api_surface_check(resources),
            self._capability_check(capability_set),
            self._ci_check(ci_passed),
        )
        pass_count = sum(1 for check in checks if check.status == ReadinessStatus.PASS)
        warn_count = sum(1 for check in checks if check.status == ReadinessStatus.WARN)
        fail_count = sum(1 for check in checks if check.status == ReadinessStatus.FAIL)
        status = self._overall_status(checks)
        return EnterpriseReadinessReport(
            status=status,
            checks=checks,
            pass_count=pass_count,
            warn_count=warn_count,
            fail_count=fail_count,
            summary=self._summary(status),
            metadata={
                "required_v1_endpoint_count": len(self.REQUIRED_V1_ENDPOINTS),
                "required_capability_count": len(self.REQUIRED_CAPABILITIES),
                "phase": "6J",
            },
        )

    def _governance_check(self, *, api_read_only: bool, governance_flags_present: bool) -> ReadinessCheck:
        if api_read_only and governance_flags_present:
            return ReadinessCheck(
                "governance_guardrails",
                "governance",
                ReadinessStatus.PASS,
                "Read-only and advisory-only production response guardrails are present.",
                ("advisory_only", "read_only", "inventory_source_of_truth_preserved"),
            )
        return ReadinessCheck(
            "governance_guardrails",
            "governance",
            ReadinessStatus.FAIL,
            "Production readiness requires read-only advisory guardrails on API responses.",
        )

    def _api_surface_check(self, stable_resources: tuple[str, ...]) -> ReadinessCheck:
        missing = tuple(endpoint for endpoint in self.REQUIRED_V1_ENDPOINTS if endpoint not in stable_resources)
        if not missing:
            return ReadinessCheck(
                "production_api_surface",
                "api",
                ReadinessStatus.PASS,
                "All required v1 production API resources are advertised.",
                stable_resources,
            )
        return ReadinessCheck(
            "production_api_surface",
            "api",
            ReadinessStatus.FAIL,
            "Required production API resources are missing.",
            missing,
        )

    def _capability_check(self, capabilities: tuple[str, ...]) -> ReadinessCheck:
        missing = tuple(capability for capability in self.REQUIRED_CAPABILITIES if capability not in capabilities)
        if not missing:
            return ReadinessCheck(
                "phase_6_capabilities",
                "capability",
                ReadinessStatus.PASS,
                "All required Phase 6 production capabilities are present.",
                capabilities,
            )
        return ReadinessCheck(
            "phase_6_capabilities",
            "capability",
            ReadinessStatus.WARN,
            "Some Phase 6 production capability markers are missing.",
            missing,
        )

    def _ci_check(self, ci_passed: bool) -> ReadinessCheck:
        if ci_passed:
            return ReadinessCheck(
                "ci_validation",
                "release",
                ReadinessStatus.PASS,
                "CI validation is expected to pass before merge.",
                ("pytest", "deployment_readiness_checks"),
            )
        return ReadinessCheck(
            "ci_validation",
            "release",
            ReadinessStatus.FAIL,
            "Enterprise readiness cannot pass without clean CI.",
        )

    def _overall_status(self, checks: tuple[ReadinessCheck, ...]) -> ReadinessStatus:
        if any(check.status == ReadinessStatus.FAIL for check in checks):
            return ReadinessStatus.FAIL
        if any(check.status == ReadinessStatus.WARN for check in checks):
            return ReadinessStatus.WARN
        return ReadinessStatus.PASS

    def _summary(self, status: ReadinessStatus) -> str:
        if status == ReadinessStatus.PASS:
            return "Phase 6 enterprise readiness checks passed."
        if status == ReadinessStatus.WARN:
            return "Phase 6 enterprise readiness passed with warnings."
        return "Phase 6 enterprise readiness failed."
