from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


REQUIRED_PHASE_9_DOCS = (
    "docs/phase_9b_api_exposure_lock.md",
    "docs/phase_9c_client_contract_examples.md",
    "docs/phase_9e_api_stability_versioning.md",
    "docs/phase_9f_openapi_contract.md",
    "docs/phase_9f_consumer_handoff.md",
    "docs/phase_9g_reference_client.md",
    "docs/phase_9h_compatibility_certification.md",
    "docs/phase_9i_enterprise_release_readiness.md",
)


REQUIRED_PHASE_9_TESTS = (
    "tests/test_phase_9a_decision_review_endpoints.py",
    "tests/test_phase_9d_api_adapter_compatibility.py",
    "tests/test_phase_9e_api_stability_versioning.py",
    "tests/test_phase_9g_decision_review_client.py",
    "tests/test_phase_9h_consumer_compatibility_certification.py",
    "tests/test_phase_9i_enterprise_release_readiness.py",
)


REQUIRED_RUNTIME_FILES = (
    "src/invyra_forecasting/decision_review_endpoints.py",
    "src/invyra_forecasting/decision_review_client.py",
)


REQUIRED_GUARDRAIL_TERMS = (
    "advisory-only",
    "read-only",
    "no inventory mutation",
    "no stock movement creation",
    "no purchase order creation",
    "no purchase order approval",
    "no export file writing",
    "no export data transmission",
    "Inventory remains the source of truth",
)


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_phase_9_release_readiness_artifacts_exist() -> None:
    for path in (*REQUIRED_PHASE_9_DOCS, *REQUIRED_PHASE_9_TESTS, *REQUIRED_RUNTIME_FILES):
        assert (ROOT / path).exists(), f"Missing Phase 9 release readiness artifact: {path}"


def test_phase_9_enterprise_release_readiness_document_locks_guardrails() -> None:
    content = _read("docs/phase_9i_enterprise_release_readiness.md")

    for term in REQUIRED_GUARDRAIL_TERMS:
        assert term in content
    assert "Phase 9 API layer is ready for controlled read-only enterprise integration" in content
    assert "Phase 9I Completion Marker" in content


def test_phase_9_runtime_surface_remains_limited_to_read_only_api_and_client_helpers() -> None:
    endpoints = _read("src/invyra_forecasting/decision_review_endpoints.py")
    client = _read("src/invyra_forecasting/decision_review_client.py")

    assert "@router.get" in endpoints
    assert "@router.post" not in endpoints
    assert "@router.put" not in endpoints
    assert "@router.patch" not in endpoints
    assert "@router.delete" not in endpoints
    assert "DecisionReviewReferenceClient" in client
    assert "def get_dashboard" in client
    assert "def get_export_bundle" in client


def test_phase_9_documentation_covers_consumer_readiness_stack() -> None:
    doc_bundle = "\n".join(_read(path) for path in REQUIRED_PHASE_9_DOCS)

    assert "OpenAPI" in doc_bundle
    assert "Consumer Integration Handoff" in doc_bundle
    assert "Read-Only Reference Client" in doc_bundle
    assert "Consumer Compatibility Certification" in doc_bundle
    assert "Enterprise Release Readiness" in doc_bundle


def test_phase_9_test_coverage_covers_public_contract_layers() -> None:
    test_bundle = "\n".join(_read(path) for path in REQUIRED_PHASE_9_TESTS)

    assert "/forecast/decision-review/dashboard" in test_bundle
    assert "/forecast/decision-review/export" in test_bundle
    assert "DecisionReviewReferenceClient" in test_bundle
    assert "Unsupported decision review export format" in test_bundle
    assert "advisory_only" in test_bundle
    assert "read_only" in test_bundle
    assert "inventory_source_of_truth_preserved" in test_bundle
