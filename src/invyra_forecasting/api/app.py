from __future__ import annotations

import sys

from invyra_forecasting.api import legacy_app as _legacy_app
from invyra_forecasting.api.evaluation_routes import router as evaluation_router


_LEGACY_STABLE_RESOURCES = _legacy_app._stable_v1_resources
_E6_STABLE_RESOURCES = (
    "/v1/evaluations",
    "/v1/evaluations/{evaluation_id}",
    "/v1/history/{history_id}/evaluation",
    "/v1/models/{model_name}/performance",
)


def _stable_v1_resources() -> tuple[str, ...]:
    return _LEGACY_STABLE_RESOURCES() + _E6_STABLE_RESOURCES


_legacy_app._stable_v1_resources = _stable_v1_resources
_legacy_app.app.include_router(evaluation_router)
sys.modules[__name__] = _legacy_app
