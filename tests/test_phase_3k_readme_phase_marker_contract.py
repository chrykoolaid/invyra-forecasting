from pathlib import Path


def test_readme_tracks_recent_phase_markers():
    readme = Path("README.md").read_text()
    expected_markers = (
        "## Phase 3F Helper Separation Contract",
        "## Phase 3G Helper Advisory Guardrail Contract",
        "## Phase 3H Service Helper Export",
        "## Phase 3I Service Import Compatibility",
        "## Phase 3J Service Import Status Notes",
    )

    for marker in expected_markers:
        assert marker in readme


def test_readme_documents_stable_service_import_paths():
    readme = Path("README.md").read_text()

    assert "from invyra_forecasting.services import ForecastingService" in readme
    assert "from invyra_forecasting.services import run_item_forecast_with_registry_intelligence" in readme
    assert "The package-level export is an integration convenience only." in readme
