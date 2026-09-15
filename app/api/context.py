# ---------------------------------------------------------------------------
# context.py — Per-request context (request / correlation IDs)
# ---------------------------------------------------------------------------
# Stores the identifiers of the currently handling request in a contextvar.
# Both the middleware (which writes them) and the response schemas (which
# read them for the envelope meta) share this module, avoiding a circular
# dependency between the two.
# ---------------------------------------------------------------------------

import contextvars
from dataclasses import dataclass


@dataclass(frozen=True)
class RequestContext:
    """Identifiers bound to one HTTP request."""

    request_id: str
    correlation_id: str


# Contextvar holding the active request (None outside any request scope).
_current: contextvars.ContextVar["RequestContext | None"] = contextvars.ContextVar(
    "request_context", default=None
)


def set_request_context(ctx: RequestContext) -> contextvars.Token:
    """Bind a request context and return the reset token."""
    return _current.set(ctx)


def reset_request_context(token: contextvars.Token) -> None:
    """Unbind the request context using the token from set_request_context."""
    _current.reset(token)


def get_request_context() -> "RequestContext | None":
    """Return the current request context, or None outside a request."""
    return _current.get()


def get_request_id() -> str:
    """Return the active request ID (empty string outside a request)."""
    ctx = _current.get()
    return ctx.request_id if ctx else ""


def get_correlation_id() -> str:
    """Return the active correlation ID (empty string outside a request)."""
    ctx = _current.get()
    return ctx.correlation_id if ctx else ""