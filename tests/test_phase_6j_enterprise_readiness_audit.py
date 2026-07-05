from __future__ import annotations

from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from invyra_forecasting.api.app import app
from invyra_forecasting.readiness import EnterpriseReadinessAuditService, ReadinessCheck, ReadinessStatus


client = TestClient(app)


def test_phase_6j_readiness_audit_passes_with_required_surface() -> None:
    service = EnterpriseReadinessAuditService()

    report = service.audit(stable_resources=service.REQUIRED_V1_ENDPOINTS)

    assert report.status == ReadinessStatus.PASS
    assert report.pass_count == 4
    assert report.warn_count == 0
    assert report.fail_count == 0
    assert report.summary == "Phase 6 enterprise readiness checks passed."
    assert report.advisory_only is True
    assert report.read_only is True
    assert report.inventory_source_of_truth_preserved is True


def test_phase_6j_readiness_audit_fails_missing_required_api() -> None:
    service = EnterpriseReadinessAuditService()
    incomplete = tuple(endpoint for endpoint in service.REQUIRED_V1_ENDPOINTS if endpoint != "/v1/hardening/summary")

    report = service.audit(stable_resources=incomplete)

    assert report.status == ReadinessStatus.FAIL
    assert report.fail_count == 1
    api_check = next(check for check in report.checks if check.check_id == "production_api_surface")
    assert api_check.status == ReadinessStatus.FAIL
    assert api_check.evidence == ("/v1/hardening/summary",)


def test_phase_6j_readiness_audit_warns_missing_capability_marker() -> None:
    service = EnterpriseReadinessAuditService()
    capabilities = tuple(
        capability for capability in service.REQUIRED_CAPABILITIES if capability != "drift_detection"
    )

    report = service.audit(stable_resources=service.REQUIRED_V1_ENDPOINTS, capabilities=capabilities)

    assert report.status == ReadinessStatus.WARN
    assert report.warn_count == 1
    capability_check = next(check for check in report.checks if check.check_id == "phase_6_capabilities")
    assert capability_check.evidence == ("drift_detection",)


def test_phase_6j_readiness_audit_fails_without_governance_flags() -> None:
    service = EnterpriseReadinessAuditService()

    report = service.audit(
        stable_resources=service.REQUIRED_V1_ENDPOINTS,
        api_read_only=False,
        governance_flags_present=False,
    )

    assert report.status == ReadinessStatus.FAIL
    governance_check = next(check for check in report.checks if check.check_id == "governance_guardrails")
    assert governance_check.status == ReadinessStatus.FAIL


def test_phase_6j_rejects_non_advisory_readiness_check() -> None:
    check = ReadinessCheck("check-1", "governance", ReadinessStatus.PASS, "ok")

    with pytest.raises(ValueError, match="readiness checks must remain advisory-only"):
        replace(check, advisory_only=False)


def test_phase_6j_readiness_api_returns_read_only_summary() -> None:
    response = client.get("/v1/readiness/summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["api_version"] == "v1"
    assert payload["resource"] == "enterprise_readiness_summary"
    assert payload["advisory_only"] is True
    assert payload["read_only"] is True
    assert payload["inventory_source_of_truth_preserved"] is True
    assert payload["data"]["status"] == "PASS"
    assert payload["data"]["pass_count"] == 4


def test_phase_6j_metadata_lists_readiness_endpoint() -> None:
    response = client.get("/v1")

    assert response.status_code == 200
    assert "/v1/readiness/summary" in response.json()["data"]["stable_resources"]
