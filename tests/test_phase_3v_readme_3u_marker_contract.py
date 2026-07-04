from pathlib import Path


def test_readme_tracks_phase_3t_and_3u_status_markers():
    readme = Path("README.md").read_text()
    markers = (
        "## Phase 3T README Phase 3S Marker Contract",
        "## Phase 3U Phase 3T Status Notes",
    )

    for marker in markers:
        assert marker in readme


def test_phase_3u_readme_status_remains_documentation_only():
    readme = Path("README.md").read_text()

    assert "Phase 3U documents Phase 3T completion" in readme
    assert "This is a documentation-only phase." in readme
    assert "It does not change runtime behavior, forecast calculations, recommendations, inventory, stock movements, or purchase-order behavior." in readme
