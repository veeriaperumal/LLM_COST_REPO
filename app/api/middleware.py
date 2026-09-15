# ---------------------------------------------------------------------------
# middleware.py — Request context, logging, and CORS middleware
# ---------------------------------------------------------------------------
# 1. RequestContextMiddleware — assigns X-Request-ID / X-Correlation-ID,
#    stores them in contextvars (read by the response envelope) and echoes
#    them back on the response headers.
#
# 2. RequestLoggingMiddleware — logs one line per request (method, path,
#    status, duration, request ID).  Request bodies are never logged.
#
# These are implemented as PURE ASGI middleware (not BaseHTTPMiddleware).
# BaseHTTPMiddleware re-raises exceptions already handled by FastAPI's
# exception handlers and leaks contextvars into extra task groups, which
# breaks both the standard response envelope and ID propagation.
#
# 3. configure_cors() — builds Starlette's CORS middleware from cors_* env.
#
# NOTE on ordering (Starlette): the LAST middleware added runs FIRST, so in
# app.main the intended execution order is CORS -> context -> logging -> route.
# ---------------------------------------------------------------------------

import logging
import time
import uuid

from fastapi.middleware.cors import CORSMiddleware

from app.api.context import (
    RequestContext,
    get_request_id,
    reset_request_context,
    set_request_context,
)
from app.config.settings import get_settings

logger = logging.getLogger("app.api.middleware")

# Header names (bytes, as carried in the ASGI scope / response messages).
_REQUEST_ID_HEADER = b"x-request-id"
_CORRELATION_ID_HEADER = b"x-correlation-id"


def _scope_header(scope: dict, name: bytes) -> bytes | None:
    """Look up a header in the ASGI scope case-insensitively."""
    for key, value in scope.get("headers", []):
        if key.lower() == name:
            return value
    return None


class RequestContextMiddleware:
    """Generate and propagate request / correlation identifiers."""

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Honour an inbound correlation ID so callers can trace across
        # services; otherwise mint fresh identifiers.
        inbound = _scope_header(scope, _CORRELATION_ID_HEADER) or b""
        correlation_id = inbound.decode() or uuid.uuid4().hex
        request_id = uuid.uuid4().hex

        # Bind to contextvars so the logging middleware and the response
        # envelope (schemas.fail/ok) read the same IDs.
        token = set_request_context(RequestContext(request_id, correlation_id))

        # Also stash on the ASGI scope: the generic-500 handler runs in
        # ServerErrorMiddleware OUTSIDE this middleware, where the contextvar
        # has already been reset, so it falls back to these values.
        state = scope.setdefault("state", {})
        state["request_id"] = request_id
        state["correlation_id"] = correlation_id

        async def send_with_headers(message: dict) -> None:
            # Attach the identifiers to the response start message so they
            # are visible to the client.
            if message["type"] == "http.response.start":
                message.setdefault("headers", []).extend(
                    [
                        (_REQUEST_ID_HEADER, request_id.encode()),
                        (_CORRELATION_ID_HEADER, correlation_id.encode()),
                    ]
                )
            await send(message)

        try:
            await self.app(scope, receive, send_with_headers)
        finally:
            reset_request_context(token)


class RequestLoggingMiddleware:
    """Log method, path, status, duration, and request ID per call."""

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "")
        path = scope.get("path", "")

        status_holder: dict[str, int] = {"status": 0}
        start = time.perf_counter()

        async def send_with_status(message: dict) -> None:
            if message["type"] == "http.response.start":
                status_holder["status"] = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_with_status)
        except BaseException:
            # Ensure we still log a 500 for failures that occur below us.
            status_holder["status"] = 500
            raise
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.info(
                "method=%s path=%s status=%d duration_ms=%.2f request_id=%s",
                method,
                path,
                status_holder["status"],
                duration_ms,
                get_request_id(),
            )


def configure_cors(app) -> None:
    """Conditionally build and attach Starlette's CORS middleware.

    ``cors_*`` settings are comma-separated strings.  Starlette forbids a
    literal ``*`` origin combined with credentials, so when the allowlist is
    ``*`` we degrade credentials to False.
    """
    settings = get_settings()

    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    methods = [m.strip() for m in settings.cors_allow_methods.split(",") if m.strip()]
    headers = [h.strip() for h in settings.cors_allow_headers.split(",") if h.strip()]

    allow_credentials = settings.cors_allow_credentials
    if "*" in origins and allow_credentials:
        allow_credentials = False

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=allow_credentials,
        allow_methods=methods,
        allow_headers=headers,
    )