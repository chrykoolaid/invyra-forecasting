from __future__ import annotations

import os
from collections.abc import Iterable

DEFAULT_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "https://app.base44.com",
]

ALLOWED_METHODS = ["GET", "POST", "OPTIONS"]
ALLOWED_HEADERS = ["Content-Type", "X-Tenant-Id", "X-Request-Id"]


def parse_allowed_origins(raw: str | None) -> list[str]:
    if raw is None or not raw.strip():
        return list(DEFAULT_ALLOWED_ORIGINS)
    origins = [origin.strip().rstrip("/") for origin in raw.split(",") if origin.strip()]
    if any(origin == "*" for origin in origins):
        raise ValueError("Configure explicit CORS origins for the forecasting API.")
    return origins


def allowed_origins_from_env() -> list[str]:
    return parse_allowed_origins(os.getenv("INVYRA_FORECASTING_ALLOWED_ORIGINS"))


def is_origin_allowed(origin: str, allowed_origins: Iterable[str] | None = None) -> bool:
    normalized = origin.strip().rstrip("/")
    return normalized in set(allowed_origins or allowed_origins_from_env())
