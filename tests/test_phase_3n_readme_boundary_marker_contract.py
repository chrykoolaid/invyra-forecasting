from pathlib import Path


def test_readme_tracks_boundary_status_markers():
    readme = Path("README.md").read_text()
    markers = (
        "## Phase 3K README Phase Marker Contract",
        "## Phase 3L Service Helper Boundary Contract",
        "## Phase 3M Boundary Status Notes",
    )

    for marker in markers:
        assert marker in readme


def test_readme_boundary_status_remains_documentation_only():
    readme = Path("README.md").read_text()

    assert "This is a documentation-only phase." in readme
    assert "It does not change runtime behavior" in readme
    assert "It does not change runtime behavior, forecast calculations, recommendations, inventory, stock movements, or purchase-order behavior." in readme
