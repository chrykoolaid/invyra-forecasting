from pathlib import Path


def test_readme_tracks_phase_3n_and_3o_status_markers():
    readme = Path("README.md").read_text()
    markers = (
        "## Phase 3N README Boundary Marker Contract",
        "## Phase 3O Phase 3N Status Notes",
    )

    for marker in markers:
        assert marker in readme


def test_phase_3o_readme_status_remains_documentation_only():
    readme = Path("README.md").read_text()

    assert "Phase 3O documents Phase 3N completion" in readme
    assert "This is a documentation-only phase." in readme
    assert "It does not change runtime behavior, forecast calculations, recommendations, inventory, stock movements, or purchase-order behavior." in readme
