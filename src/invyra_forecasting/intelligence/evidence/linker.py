from __future__ import annotations

from invyra_forecasting.intelligence.objects import EvidenceLink
from invyra_forecasting.signals.schema import ForecastSignal


class EvidenceLinker:
    """Carries signal evidence into forecast intelligence outputs."""

    def link(self, signals: list[ForecastSignal]) -> list[EvidenceLink]:
        links: list[EvidenceLink] = []
        for signal in signals:
            if signal.evidence_ref is None:
                continue
            links.append(
                EvidenceLink(
                    signal_id=signal.signal_id,
                    evidence_ref=signal.evidence_ref,
                    module_source=signal.module_source.value,
                    signal_type=signal.signal_type.value,
                    reason_code=signal.reason_code,
                )
            )
        return links
