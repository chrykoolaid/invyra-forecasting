from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any, Iterable


class FailureSeverity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class RecoveryAction(StrEnum):
    NONE = "NONE"
    RETRY = "RETRY"
    FALLBACK = "FALLBACK"
    HUMAN_REVIEW = "HUMAN_REVIEW"


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    backoff_seconds: float = 1.0
    retryable_failures: tuple[str, ...] = ("timeout", "temporary_io", "transient_dependency")
    advisory_only: bool = True
    read_only: bool = True

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if self.backoff_seconds < 0:
            raise ValueError("backoff_seconds must be greater than or equal to 0")
        if not self.advisory_only:
            raise ValueError("retry policies must remain advisory-only")
        if not self.read_only:
            raise ValueError("retry policies must remain read-only")

    def should_retry(self, failure_type: str, attempt: int) -> bool:
        return failure_type in self.retryable_failures and attempt < self.max_attempts

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["retryable_failures"] = list(self.retryable_failures)
        return payload


@dataclass(frozen=True)
class FailureClassification:
    failure_type: str
    severity: FailureSeverity
    recovery_action: RecoveryAction
    explanation: str
    retryable: bool
    advisory_only: bool = True
    read_only: bool = True
    inventory_source_of_truth_preserved: bool = True

    def __post_init__(self) -> None:
        if not self.failure_type:
            raise ValueError("failure_type is required")
        if not self.explanation:
            raise ValueError("explanation is required")
        if not self.advisory_only:
            raise ValueError("failure classifications must remain advisory-only")
        if not self.read_only:
            raise ValueError("failure classifications must remain read-only")
        if not self.inventory_source_of_truth_preserved:
            raise ValueError("inventory source of truth must be preserved")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["severity"] = self.severity.value
        payload["recovery_action"] = self.recovery_action.value
        return payload


@dataclass(frozen=True)
class RecoveryRecord:
    recovery_id: str
    failure_type: str
    attempt: int
    action: RecoveryAction
    success: bool
    message: str
    metadata: dict[str, Any] = field(default_factory=dict)
    advisory_only: bool = True
    read_only: bool = True
    inventory_source_of_truth_preserved: bool = True

    def __post_init__(self) -> None:
        if not self.recovery_id:
            raise ValueError("recovery_id is required")
        if not self.failure_type:
            raise ValueError("failure_type is required")
        if self.attempt < 1:
            raise ValueError("attempt must be at least 1")
        if not self.message:
            raise ValueError("message is required")
        if not self.advisory_only:
            raise ValueError("recovery records must remain advisory-only")
        if not self.read_only:
            raise ValueError("recovery records must remain read-only")
        if not self.inventory_source_of_truth_preserved:
            raise ValueError("inventory source of truth must be preserved")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["action"] = self.action.value
        return payload


@dataclass(frozen=True)
class HardeningSummary:
    recovery_count: int
    successful_recoveries: int
    failed_recoveries: int
    failure_counts: dict[str, int]
    action_counts: dict[str, int]
    critical_failure_count: int
    warnings: tuple[str, ...]
    advisory_only: bool = True
    read_only: bool = True
    inventory_source_of_truth_preserved: bool = True

    def __post_init__(self) -> None:
        if not self.advisory_only:
            raise ValueError("hardening summaries must remain advisory-only")
        if not self.read_only:
            raise ValueError("hardening summaries must remain read-only")
        if not self.inventory_source_of_truth_preserved:
            raise ValueError("inventory source of truth must be preserved")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["warnings"] = list(self.warnings)
        return payload


class InMemoryRecoveryRepository:
    def __init__(self, records: Iterable[RecoveryRecord] = ()) -> None:
        self._records: dict[str, RecoveryRecord] = {}
        for record in records:
            self.record(record)

    def record(self, record: RecoveryRecord) -> RecoveryRecord:
        if record.recovery_id in self._records:
            raise ValueError(f"recovery already recorded: {record.recovery_id}")
        self._records[record.recovery_id] = record
        return record

    def all(self) -> tuple[RecoveryRecord, ...]:
        return tuple(self._records.values())


class ProductionHardeningService:
    def __init__(self, repository: InMemoryRecoveryRepository | None = None, retry_policy: RetryPolicy | None = None) -> None:
        self._repository = repository or InMemoryRecoveryRepository()
        self._retry_policy = retry_policy or RetryPolicy()

    def classify_failure(self, failure_type: str, *, attempt: int = 1) -> FailureClassification:
        retryable = self._retry_policy.should_retry(failure_type, attempt)
        if failure_type in {"invalid_input", "governance_violation"}:
            return FailureClassification(
                failure_type=failure_type,
                severity=FailureSeverity.CRITICAL if failure_type == "governance_violation" else FailureSeverity.WARNING,
                recovery_action=RecoveryAction.HUMAN_REVIEW,
                explanation="Failure requires human review and must not trigger operational mutation.",
                retryable=False,
            )
        if retryable:
            return FailureClassification(
                failure_type=failure_type,
                severity=FailureSeverity.WARNING,
                recovery_action=RecoveryAction.RETRY,
                explanation="Failure appears transient and may be retried within the configured policy.",
                retryable=True,
            )
        return FailureClassification(
            failure_type=failure_type,
            severity=FailureSeverity.INFO,
            recovery_action=RecoveryAction.NONE,
            explanation="Failure is not classified as retryable by the current policy.",
            retryable=False,
        )

    def record_recovery(self, record: RecoveryRecord) -> RecoveryRecord:
        return self._repository.record(record)

    def summarize(self, classifications: Iterable[FailureClassification] = ()) -> HardeningSummary:
        records = self._repository.all()
        failure_counts: dict[str, int] = {}
        action_counts: dict[str, int] = {}
        for record in records:
            failure_counts[record.failure_type] = failure_counts.get(record.failure_type, 0) + 1
            action_counts[record.action.value] = action_counts.get(record.action.value, 0) + 1
        critical_failure_count = sum(1 for classification in classifications if classification.severity == FailureSeverity.CRITICAL)
        warnings: list[str] = []
        failed = len(tuple(record for record in records if not record.success))
        if failed:
            warnings.append(f"{failed} recovery attempt(s) failed.")
        if critical_failure_count:
            warnings.append(f"{critical_failure_count} critical failure classification(s) observed.")
        return HardeningSummary(
            recovery_count=len(records),
            successful_recoveries=len(tuple(record for record in records if record.success)),
            failed_recoveries=failed,
            failure_counts=failure_counts,
            action_counts=action_counts,
            critical_failure_count=critical_failure_count,
            warnings=tuple(warnings),
        )

    @property
    def retry_policy(self) -> RetryPolicy:
        return self._retry_policy
