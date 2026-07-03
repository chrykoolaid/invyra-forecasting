from invyra_forecasting.intelligence_summary import ForecastIntelligenceSummary


def test_intelligence_summary_is_serializable_context_object():
    summary = ForecastIntelligenceSummary(
        item_id="ITEM-001",
        location_id="LOC-001",
        environment="TEST",
        signal_count=2,
        confidence=0.75,
        audit_refs=("MOV-001", "SNAPSHOT-001"),
        quality_scores=(0.9, 0.8),
        weighted_scores=(0.9, 0.6),
        feature_summary={"latest_on_hand": 12, "total_outbound_quantity": 3},
        governance={"advisory_only": True, "source_of_truth_preserved": True},
    )

    payload = summary.to_dict()

    assert payload["item_id"] == "ITEM-001"
    assert payload["location_id"] == "LOC-001"
    assert payload["environment"] == "TEST"
    assert payload["signal_count"] == 2
    assert payload["confidence"] == 0.75
    assert payload["audit_refs"] == ("MOV-001", "SNAPSHOT-001")
    assert payload["feature_summary"]["latest_on_hand"] == 12
    assert payload["governance"]["advisory_only"] is True


def test_empty_intelligence_summary_defaults_are_safe():
    summary = ForecastIntelligenceSummary(
        item_id="ITEM-404",
        location_id="LOC-001",
        environment="TEST",
        signal_count=0,
        confidence=0.0,
    )

    assert summary.audit_refs == ()
    assert summary.quality_scores == ()
    assert summary.weighted_scores == ()
    assert summary.feature_summary == {}
    assert summary.governance == {}
