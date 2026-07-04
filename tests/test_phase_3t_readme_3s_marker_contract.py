from pathlib import Path


def test_readme_tracks_phase_3r_and_3s_status_markers():
    readme = Path("README.md").read_text()
    markers = (
        "## Phase 3R README Phase 3Q Marker Contract",
        "## Phase 3S Phase 3R Status Notes",
    )

    for marker in markers:
        assert marker in readme


def test_phase_3s_readme_status_remains_documentation_only():
    readme = Path("README.md").read_text()

    assert "Phase 3S documents Phase 3R completion" in readme
    assert "This is a documentation-only phase." in readme
    assert "It does not change runtime behavior, forecast calculations, recommendations, inventory, stock movements, or purchase-order behavior." in readme
