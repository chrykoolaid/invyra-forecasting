from __future__ import annotations

from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from invyra_forecasting.api.app import app
from invyra_forecasting.hardening import (
    FailureSeverity,
    InMemoryRecoveryRepository,
    ProductionHardeningService,
    RecoveryAction,
    RecoveryRecord,
    RetryPolicy,
)


client = TestClient(app)


def test_phase_6i_retry_policy_classifies_retryable_failures() -> None:
    policy = RetryPolicy(max_attempts=3, backoff_seconds=0.5)

    assert policy.should_retry("timeout", 1) is True
    assert policy.should_retry("timeout", 3) is False
    assert policy.should_retry("invalid_input", 1) is False
    assert policy.to_dict()["retryable_failures"] == ["timeout", "temporary_io", "transient_dependency"]


def test_phase_6i_classifies_transient_and_governance_failures() -> None:
    service = ProductionHardeningService()

    transient = service.classify_failure("timeout", attempt=1)
    governance = service.classify_failure("governance_violation", attempt=1)

    assert transient.retryable is True
    assert transient.recovery_action == RecoveryAction.RETRY
    assert transient.severity == FailureSeverity.WARNING
    assert governance.retryable is False
    assert governance.recovery_action == RecoveryAction.HUMAN_REVIEW
    assert governance.severity == FailureSeverity.CRITICAL
    assert governance.inventory_source_of_truth_preserved is True


def test_phase_6i_summarizes_recovery_records_and_classifications() -> None:
    service = ProductionHardeningService(
        InMemoryRecoveryRepository(
            (
                RecoveryRecord("recovery-1", "timeout", 1, RecoveryAction.RETRY, True, "retry succeeded"),
                RecoveryRecord("recovery-2", "temporary_io", 1, RecoveryAction.RETRY, False, "retry failed"),
            )
        )
    )
    critical = service.classify_failure("governance_violation")

    summary = service.summarize((critical,))

    assert summary.recovery_count == 2
    assert summary.successful_recoveries == 1
    assert summary.failed_recoveries == 1
    assert summary.failure_counts == {"timeout": 1, "temporary_io": 1}
    assert summary.action_counts == {"RETRY": 2}
    assert summary.critical_failure_count == 1
    assert len(summary.warnings) == 2
    assert summary.advisory_only is True
    assert summary.read_only is True


def test_phase_6i_rejects_invalid_hardening_records() -> None:
    with pytest.raises(ValueError, match="max_attempts must be"):
        RetryPolicy(max_attempts=0)

    with pytest.raises(ValueError, match="attempt must be"):
        RecoveryRecord("recovery-1", "timeout", 0, RecoveryAction.RETRY, False, "invalid")

    record = RecoveryRecord("recovery-1", "timeout", 1, RecoveryAction.RETRY, True, "ok")
    with pytest.raises(ValueError, match="recovery records must remain advisory-only"):
        replace(record, advisory_only=False)


def test_phase_6i_rejects_duplicate_recovery_records() -> None:
    repository = InMemoryRecoveryRepository()
    repository.record(RecoveryRecord("recovery-1", "timeout", 1, RecoveryAction.RETRY, True, "ok"))

    with pytest.raises(ValueError, match="recovery already recorded"):
        repository.record(RecoveryRecord("recovery-1", "timeout", 1, RecoveryAction.RETRY, True, "duplicate"))


def test_phase_6i_hardening_api_returns_read_only_summary() -> None:
    response = client.get("/v1/hardening/summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["api_version"] == "v1"
    assert payload["resource"] == "hardening_summary"
    assert payload["advisory_only"] is True
    assert payload["read_only"] is True
    assert payload["inventory_source_of_truth_preserved"] is True
    assert payload["data"]["recovery_count"] == 0
    assert payload["metadata"]["retry_policy"]["max_attempts"] == 3


def test_phase_6i_metadata_lists_hardening_endpoint() -> None:
    response = client.get("/v1")

    assert response.status_code == 200
    assert "/v1/hardening/summary" in response.json()["data"]["stable_resources"]
