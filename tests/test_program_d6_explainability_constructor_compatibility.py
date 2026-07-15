from __future__ import annotations

from invyra_forecasting.explainability_archive import HistoricalExplainabilityRecord


def test_legacy_positional_constructor_preserves_existing_field_order() -> None:
    archived_at_utc = "2026-07-15T13:30:00+00:00"

    record = HistoricalExplainabilityRecord(
        "archive-d6-legacy",
        "history-d6-legacy",
        "forecast-d6-legacy",
        "seasonal-naive",
        "1.0",
        0.82,
        ("Demand trend increased.",),
        ("evidence-1",),
        ("Stable seasonal pattern.",),
        {"mae": 1.25},
        archived_at_utc,
        True,
        True,
        True,
    )

    assert record.archived_at_utc == archived_at_utc
    assert record.advisory_only is True
    assert record.read_only is True
    assert record.inventory_source_of_truth_preserved is True
    assert record.metadata == {}


def test_new_metadata_remains_available_by_keyword() -> None:
    record = HistoricalExplainabilityRecord(
        archive_id="archive-d6-metadata",
        history_id="history-d6-metadata",
        forecast_id="forecast-d6-metadata",
        model_name="seasonal-naive",
        model_version="1.0",
        confidence=0.82,
        explanation=("Demand trend increased.",),
        evidence_refs=("evidence-1",),
        metadata={"request_id": "request-d6"},
    )

    assert record.metadata == {"request_id": "request-d6"}


def test_serialized_contract_still_contains_request_metadata() -> None:
    record = HistoricalExplainabilityRecord(
        archive_id="archive-d6-serialized",
        history_id="history-d6-serialized",
        forecast_id="forecast-d6-serialized",
        model_name="seasonal-naive",
        model_version="1.0",
        confidence=0.82,
        explanation=("Demand trend increased.",),
        evidence_refs=("evidence-1",),
        metadata={"request_id": "request-d6-serialized"},
    )

    payload = record.to_dict()

    assert payload["metadata"]["request_id"] == "request-d6-serialized"
    assert payload["advisory_only"] is True
    assert payload["read_only"] is True
    assert payload["inventory_source_of_truth_preserved"] is True
