from __future__ import annotations

from invyra_forecasting.signals.schema import ForecastSignal


def build_evidence_chain(signal: ForecastSignal) -> tuple[str, ...]:
    """Build an immutable evidence chain for explainable forecasting."""

    chain: list[str] = [signal.signal_id]
    if signal.evidence_ref:
        chain.append(signal.evidence_ref)

    metadata_refs = signal.metadata.get("evidence_refs")
    if isinstance(metadata_refs, (list, tuple)):
        chain.extend(str(ref) for ref in metadata_refs if str(ref).strip())

    return tuple(dict.fromkeys(chain))
