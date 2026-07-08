from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_phase_10b_desktop_adapter_contract_document_exists() -> None:
    assert (ROOT / "docs/phase_10b_desktop_adapter_contracts.md").exists()


def test_phase_10b_contract_limits_adapter_inputs_to_read_only_endpoints() -> None:
    content = _read("docs/phase_10b_desktop_adapter_contracts.md")

    assert "GET /forecast/decision-review/dashboard" in content
    assert "GET /forecast/decision-review/export" in content
    assert "GET /forecast/decision-review/export?export_format=dict" in content
    assert "DecisionReviewReferenceClient" in content


def test_phase_10b_contract_defines_desktop_view_model_examples() -> None:
    content = _read("docs/phase_10b_desktop_adapter_contracts.md")

    assert "DesktopForecastReviewSummaryCard" in content
    assert "DesktopForecastExportPreview" in content
    assert "Forecast advisory only" in content
    assert "Export projection only" in content


def test_phase_10b_contract_requires_fail_closed_governance_validation() -> None:
    content = _read("docs/phase_10b_desktop_adapter_contracts.md")

    assert "advisory_only == true" in content
    assert "read_only == true" in content
    assert "inventory_source_of_truth_preserved == true" in content
    assert "fail closed" in content
    assert "ignore unknown optional fields" in content


def test_phase_10b_contract_preserves_operational_boundary() -> None:
    content = _read("docs/phase_10b_desktop_adapter_contracts.md")

    assert "must not:" in content
    assert "create stock movements" in content
    assert "create purchase orders" in content
    assert "approve purchase orders" in content
    assert "mutate Inventory" in content
    assert "update the stock ledger" in content
    assert "write export files" in content
    assert "transmit export data" in content
    assert "Inventory remains source of truth" in content


def test_phase_10b_does_not_add_desktop_runtime_implementation() -> None:
    content = _read("docs/phase_10b_desktop_adapter_contracts.md")

    assert "does not add desktop runtime behavior" in content
    assert "no desktop runtime implementation" in content
    assert "no runtime behavior changes" in content
    assert "no endpoint behavior changes" in content
