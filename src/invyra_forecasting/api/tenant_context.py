from __future__ import annotations

from contextvars import ContextVar
from uuid import uuid4

TENANT_HEADER_NAME = "X-Tenant-Id"
REQUEST_ID_HEADER_NAME = "X-Request-Id"
MAX_REQUEST_ID_LENGTH = 128
_TENANT_ID: ContextVar[str | None] = ContextVar("invyra_forecasting_tenant_id", default=None)
_REQUEST_ID: ContextVar[str | None] = ContextVar("invyra_forecasting_request_id", default=None)


def current_tenant_id() -> str | None:
    return _TENANT_ID.get()


def current_request_id() -> str | None:
    return _REQUEST_ID.get()


def normalize_tenant_id(raw: str | None) -> str | None:
    if raw is None:
        return None
    tenant_id = raw.strip()
    return tenant_id or None


def normalize_request_id(raw: str | None) -> str | None:
    if raw is None:
        return None
    request_id = raw.strip()
    if not request_id or len(request_id) > MAX_REQUEST_ID_LENGTH:
        return None
    if any(ord(character) < 32 or ord(character) > 126 for character in request_id):
        return None
    return request_id


class TenantContextMiddleware:
    """Propagate tenant and request identifiers without introducing storage or mutation."""

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        raw_tenant_id = None
        raw_request_id = None
        for name, value in scope.get("headers", ()):
            normalized_name = name.lower()
            if normalized_name == b"x-tenant-id" and raw_tenant_id is None:
                raw_tenant_id = value.decode("latin-1")
            elif normalized_name == b"x-request-id" and raw_request_id is None:
                raw_request_id = value.decode("latin-1")

        tenant_id = normalize_tenant_id(raw_tenant_id)
        request_id = normalize_request_id(raw_request_id) or str(uuid4())
        tenant_token = _TENANT_ID.set(tenant_id)
        request_token = _REQUEST_ID.set(request_id)

        async def send_with_context(message) -> None:
            if message.get("type") == "http.response.start":
                headers = list(message.get("headers", ()))
                headers.append((b"x-request-id", request_id.encode("ascii")))
                if tenant_id is not None:
                    headers.append((b"x-tenant-id", tenant_id.encode("latin-1")))
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_with_context)
        finally:
            _REQUEST_ID.reset(request_token)
            _TENANT_ID.reset(tenant_token)
