def test_phase_5_surface_imports_are_available():
    from invyra_forecasting.confidence import ConfidenceCalibrationService
    from invyra_forecasting.enterprise import EnterpriseForecastSnapshotService
    from invyra_forecasting.evaluation import ForecastEvaluationService
    from invyra_forecasting.evidence import EvidenceRankingService
    from invyra_forecasting.features import FeatureEngineeringService
    from invyra_forecasting.intelligence import ForecastIntelligenceV2Builder
    from invyra_forecasting.models import ForecastModelOrchestrator
    from invyra_forecasting.registry import ModelLifecycleRegistry

    assert FeatureEngineeringService is not None
    assert ForecastIntelligenceV2Builder is not None
    assert ForecastModelOrchestrator is not None
    assert ConfidenceCalibrationService is not None
    assert EvidenceRankingService is not None
    assert ForecastEvaluationService is not None
    assert ModelLifecycleRegistry is not None
    assert EnterpriseForecastSnapshotService is not None


def test_phase_5_locked_guardrail_terms_are_documented():
    audit_text = open("docs/phase_5_completion_audit.md", encoding="utf-8").read()

    assert "advisory-only" in audit_text
    assert "read-only" in audit_text
    assert "modify inventory" in audit_text
    assert "create stock movements" in audit_text
    assert "create purchase orders" in audit_text
    assert "approve purchase orders" in audit_text
    assert "override ledger truth" in audit_text
    assert "Base44-dependent" in audit_text
    assert "Inventory as the system of record" in audit_text
