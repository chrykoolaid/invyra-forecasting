from pathlib import Path


def test_readme_tracks_phase_3p_and_3q_status_markers():
    readme = Path("README.md").read_text()
    markers = (
        "## Phase 3P README Phase 3O Marker Contract",
        "## Phase 3Q Phase 3P Status Notes",
    )

    for marker in markers:
        assert marker in readme


def test_phase_3q_readme_status_remains_documentation_only():
    readme = Path("README.md").read_text()

    assert "Phase 3Q documents Phase 3P completion" in readme
    assert "This is a documentation-only phase." in readme
    assert "It does not change runtime behavior, forecast calculations, recommendations, inventory, stock movements, or purchase-order behavior." in readme
