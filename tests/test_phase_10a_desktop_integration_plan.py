from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_phase_10a_desktop_integration_plan_exists() -> None:
    assert (ROOT / "docs/phase_10a_desktop_integration_plan.md").exists()


def test_phase_10a_desktop_plan_preserves_read_only_api_surface() -> None:
    content = _read("docs/phase_10a_desktop_integration_plan.md")

    assert "GET /forecast/decision-review/dashboard" in content
    assert "GET /forecast/decision-review/export" in content
    assert "GET /forecast/decision-review/export?export_format=dict" in content
    assert "creating stock movements" in content
    assert "creating purchase orders" in content
    assert "approving purchase orders" in content


def test_phase_10a_desktop_plan_requires_governance_flag_validation() -> None:
    content = _read("docs/phase_10a_desktop_integration_plan.md")

    assert "advisory_only == true" in content
    assert "read_only == true" in content
    assert "inventory_source_of_truth_preserved == true" in content
    assert "fail closed" in content


def test_phase_10a_desktop_plan_locks_no_runtime_behavior() -> None:
    content = _read("docs/phase_10a_desktop_integration_plan.md")

    assert "does not add runtime behavior" in content
    assert "no API behavior changes" in content
    assert "no desktop runtime implementation" in content
    assert "no inventory mutation" in content
    assert "no stock movement creation" in content
    assert "no purchase order creation" in content
    assert "no purchase order approval" in content
    assert "no export file writing" in content
    assert "no export data transmission" in content
    assert "Inventory remains source of truth" in content


def test_phase_10a_builds_on_locked_phase_9_assets() -> None:
    assert (ROOT / "src/invyra_forecasting/decision_review_client.py").exists()
    assert (ROOT / "src/invyra_forecasting/decision_review_endpoints.py").exists()
    assert (ROOT / "docs/phase_9i_enterprise_release_readiness.md").exists()
