from __future__ import annotations

from typing import Any

from invyra_forecasting.signals.schema import ForecastSignal


def extract_signal_features(signal: ForecastSignal) -> dict[str, Any]:
    """Extract model-ready features from a normalized signal.

    Features are derived from the signal copy only. The operational source of
    truth remains owned by Inventory, ScanOps, POS, or the publishing module.
    """

    return {
        "signal_type": signal.signal_type.value,
        "module_source": signal.module_source.value,
        "direction": signal.direction.value,
        "quantity": signal.quantity,
        "unit": signal.unit,
        "has_evidence": signal.evidence_ref is not None,
        "has_reason_code": signal.reason_code is not None,
        "metadata_keys": tuple(sorted(signal.metadata.keys())),
        "event_version": signal.event_version,
    }
