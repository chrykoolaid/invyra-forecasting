from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    ROOT / "RELEASE_NOTES.md",
    ROOT / "docs" / "14_PHASE1_ACCEPTANCE_CHECKLIST.md",
    ROOT / "docs" / "15_KNOWN_LIMITATIONS.md",
    ROOT / "docs" / "16_INTEGRATION_READINESS_MATRIX.md",
    ROOT / "docs" / "17_PHASE2_CARRYOVER_SCOPE.md",
]


def test_release_readiness_files_exist():
    for path in REQUIRED_FILES:
        assert path.exists(), path
        assert path.read_text(encoding="utf-8").strip(), path


def test_release_notes_lock_governance_and_phase_two_direction():
    text = (ROOT / "RELEASE_NOTES.md").read_text(encoding="utf-8")
    assert "Forecasting is advisory only" in text
    assert "Inventory ledger remains the source of truth" in text
    assert "stable foundation for Phase 2" in text


def test_acceptance_checklist_covers_core_api_persistence_and_governance():
    text = (ROOT / "docs" / "14_PHASE1_ACCEPTANCE_CHECKLIST.md").read_text(encoding="utf-8")
    for phrase in ["Core Engine", "API and Contracts", "Persistence and Evidence", "Accuracy and Confidence", "Governance", "CI"]:
        assert phrase in text


def test_known_limitations_prevent_overclaiming():
    text = (ROOT / "docs" / "15_KNOWN_LIMITATIONS.md").read_text(encoding="utf-8")
    assert "not a commercial deployment sign-off" in text
    assert "Advanced ML is not included yet" in text
    assert "API authentication is not implemented yet" in text


def test_phase_two_carryover_keeps_inventory_first_and_advisory():
    text = (ROOT / "docs" / "17_PHASE2_CARRYOVER_SCOPE.md").read_text(encoding="utf-8")
    assert "Inventory Item Details" in text
    assert "Forecasting is advisory only" in text
    assert "Do not auto-create purchase orders" in text
    assert "Do not auto-adjust stock" in text
