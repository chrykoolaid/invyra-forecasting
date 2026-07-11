from __future__ import annotations

from contextvars import ContextVar

TENANT_HEADER_NAME = "X-Tenant-Id"
_TENANT_ID: ContextVar[str | None] = ContextVar("invyra_forecasting_tenant_id", default=None)


def current_tenant_id() -> str | None:
    return _TENANT_ID.get()


def normalize_tenant_id(raw: str | None) -> str | None:
    if raw is None:
        return None
    tenant_id = raw.strip()
    return tenant_id or None


class TenantContextMiddleware:
    """Propagate an optional tenant identifier without introducing tenant storage."""

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        raw_tenant_id = None
        for name, value in scope.get("headers", ()):
            if name.lower() == b"x-tenant-id":
                raw_tenant_id = value.decode("latin-1")
                break

        tenant_id = normalize_tenant_id(raw_tenant_id)
        token = _TENANT_ID.set(tenant_id)

        async def send_with_tenant(message) -> None:
            if tenant_id is not None and message.get("type") == "http.response.start":
                headers = list(message.get("headers", ()))
                headers.append((b"x-tenant-id", tenant_id.encode("latin-1")))
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_with_tenant)
        finally:
            _TENANT_ID.reset(token)
