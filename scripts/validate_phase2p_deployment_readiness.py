from __future__ import annotations

import os
import sys
from urllib.parse import urlparse

REQUIRED_HOSTED_ORIGIN = "https://app.base44.com"
LOCAL_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0"}


def fail(message: str) -> None:
    print(f"Phase 2P deployment readiness validation failed: {message}", file=sys.stderr)
    raise SystemExit(1)


def warn(message: str) -> None:
    print(f"Phase 2P warning: {message}")


def split_origins(raw: str) -> list[str]:
    return [origin.strip().rstrip("/") for origin in raw.split(",") if origin.strip()]


def validate_origin(origin: str) -> None:
    parsed = urlparse(origin)
    if parsed.scheme not in {"https", "http"} or not parsed.netloc:
        fail(f"CORS origin is not a valid absolute HTTP(S) origin: {origin}")
    if parsed.scheme != "https" and parsed.hostname not in LOCAL_HOSTS:
        fail(f"Hosted CORS origins must use HTTPS: {origin}")
    if parsed.path not in {"", "/"}:
        fail(f"CORS origin must not include a path: {origin}")


def main() -> None:
    raw_origins = os.getenv("INVYRA_FORECASTING_ALLOWED_ORIGINS", "")
    if not raw_origins.strip():
        fail("INVYRA_FORECASTING_ALLOWED_ORIGINS is required for hosted deployment.")

    origins = split_origins(raw_origins)
    if any(origin == "*" for origin in origins):
        fail("Wildcard CORS origin is forbidden. Configure exact hosted origins.")

    for origin in origins:
        validate_origin(origin)

    if REQUIRED_HOSTED_ORIGIN not in origins:
        warn(f"{REQUIRED_HOSTED_ORIGIN} is not present. Add it unless Base44 supplies a more specific hosted origin.")

    port = os.getenv("PORT") or os.getenv("INVYRA_FORECASTING_PORT") or "8000"
    if not port.isdigit() or int(port) <= 0:
        fail("PORT/INVYRA_FORECASTING_PORT must be a positive integer when set.")

    print("Phase 2P deployment readiness validation passed.")


if __name__ == "__main__":
    main()
