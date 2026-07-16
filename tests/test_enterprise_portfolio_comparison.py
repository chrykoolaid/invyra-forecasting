import pytest

from invyra_forecasting.enterprise_intelligence_summary import (
    EnterpriseForecastIntelligenceSummary,
    EnterpriseModelIntelligence,
)
from invyra_forecasting.enterprise_portfolio_comparison import EnterprisePortfolioComparisonService


def _summary(*, as_of: str, evaluations: int, accuracy: float | None, calibration: float | None, evidence: str):
    model = EnterpriseModelIntelligence(
        registry_id="model-a",
        model_name="seasonal-naive",
        model_version="1.0",
        lifecycle_status="active",
        forecast_horizon_days=7,
        confidence_status="trusted",
        eligible_evaluation_count=evaluations,
        average_accuracy_score=accuracy,
        average_calibration_gap=calibration,
        bias=0.0,
        evidence_refs=(evidence,),
    )
    return EnterpriseForecastIntelligenceSummary(
        namespace="tenant-a",
        as_of_utc=as_of,
        model_version_count=1,
        evaluated_model_version_count=1,
        total_eligible_evaluation_count=evaluations,
        confidence_distribution={"trusted": 1},
        weighted_average_accuracy_score=accuracy,
        weighted_average_calibration_gap=calibration,
        models=(model,),
    )


def test_computes_signed_deltas_without_declaring_a_winner() -> None:
    comparison = EnterprisePortfolioComparisonService().compare(
        _summary(as_of="2026-07-01T00:00:00+00:00", evaluations=20, accuracy=0.8, calibration=0.2, evidence="eval-old"),
        _summary(as_of="2026-07-15T00:00:00+00:00", evaluations=35, accuracy=0.86, calibration=0.15, evidence="eval-new"),
    )
    assert comparison.eligible_evaluation_count_delta == 15
    assert comparison.accuracy_delta == 0.06
    assert comparison.calibration_gap_delta == -0.05
    assert comparison.evidence_refs == ("eval-new", "eval-old")
    assert all("winner" not in reason for reason in comparison.comparison_reasons)
    assert comparison.advisory_only is True
    assert comparison.read_only is True


def test_incomplete_metrics_produce_no_invented_delta() -> None:
    comparison = EnterprisePortfolioComparisonService().compare(
        _summary(as_of="2026-07-01T00:00:00+00:00", evaluations=20, accuracy=None, calibration=0.2, evidence="eval-old"),
        _summary(as_of="2026-07-15T00:00:00+00:00", evaluations=35, accuracy=0.86, calibration=None, evidence="eval-new"),
    )
    assert comparison.accuracy_delta is None
    assert comparison.calibration_gap_delta is None


def test_rejects_reverse_chronology_and_cross_tenant_comparison() -> None:
    baseline = _summary(as_of="2026-07-15T00:00:00+00:00", evaluations=20, accuracy=0.8, calibration=0.2, evidence="eval-old")
    current = _summary(as_of="2026-07-01T00:00:00+00:00", evaluations=35, accuracy=0.86, calibration=0.15, evidence="eval-new")
    with pytest.raises(ValueError, match="must not precede"):
        EnterprisePortfolioComparisonService().compare(baseline, current)

    other = EnterpriseForecastIntelligenceSummary(**{**current.__dict__, "namespace": "tenant-b", "as_of_utc": "2026-07-16T00:00:00+00:00"})
    with pytest.raises(ValueError, match="matching tenant namespaces"):
        EnterprisePortfolioComparisonService().compare(baseline, other)
