import pytest

from invyra_forecasting.api.runtime import (
    ALLOWED_HEADERS,
    ALLOWED_METHODS,
    DEFAULT_ALLOWED_ORIGINS,
    allowed_origins_from_env,
    is_origin_allowed,
    parse_allowed_origins,
)


def test_default_allowed_origins_include_local_vite_and_base44_preview(monkeypatch):
    monkeypatch.delenv("INVYRA_FORECASTING_ALLOWED_ORIGINS", raising=False)

    origins = allowed_origins_from_env()

    assert "http://localhost:5173" in origins
    assert "http://127.0.0.1:5173" in origins
    assert "https://app.base44.com" in origins


def test_parse_allowed_origins_trims_spaces_and_trailing_slashes():
    origins = parse_allowed_origins(" https://app.base44.com/, https://example.test ")

    assert origins == ["https://app.base44.com", "https://example.test"]


def test_parse_allowed_origins_rejects_wildcard():
    with pytest.raises(ValueError, match="explicit CORS origins"):
        parse_allowed_origins("*")


def test_is_origin_allowed_uses_normalized_origin():
    assert is_origin_allowed("https://app.base44.com/", ["https://app.base44.com"])
    assert not is_origin_allowed("https://evil.example", ["https://app.base44.com"])


def test_cors_methods_and_headers_are_limited():
    assert ALLOWED_METHODS == ["GET", "POST", "OPTIONS"]
    assert ALLOWED_HEADERS == ["Content-Type", "X-Tenant-Id"]
