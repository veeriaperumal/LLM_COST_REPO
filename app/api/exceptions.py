# ---------------------------------------------------------------------------
# exceptions.py — Centralized error handling for the API
# ---------------------------------------------------------------------------
# Defines an AppError hierarchy whose members carry both an HTTP status code
# and a stable machine-readable code, then registers FastAPI exception
# handlers that serialize every failure into the standard response envelope.
# ---------------------------------------------------------------------------

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.context import get_request_id
from app.api.schemas import fail
from app.config.settings import get_settings

logger = logging.getLogger("app.api")


class AppError(Exception):
    """Base class for every controlled API error.

    Subclasses set sensible ``status_code`` / ``code`` defaults; instances
    may override either at construction time.
    """

    status_code: int = 500
    code: str = "ERROR"

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        code: str | None = None,
        details: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details
        if status_code is not None:
            self.status_code = status_code
        if code is not None:
            self.code = code


class NotFoundError(AppError):
    status_code = 404
    code = "NOT_FOUND"


class InvalidInputError(AppError):
    status_code = 400
    code = "INVALID_INPUT"


class UnauthorizedError(AppError):
    status_code = 401
    code = "UNAUTHORIZED"


class BudgetExceededError(AppError):
    status_code = 429
    code = "BUDGET_EXCEEDED"


class UpstreamError(AppError):
    status_code = 502
    code = "UPSTREAM_ERROR"


class ServiceUnavailableError(AppError):
    status_code = 503
    code = "SERVICE_UNAVAILABLE"


# -- Envelope helpers --------------------------------------------------------

def _error_response(
    status_code: int,
    code: str,
    message: str,
    details: Any | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    """Serialize an error into the standard envelope."""
    return JSONResponse(
        status_code=status_code,
        content=fail(code, message, details).model_dump(),
        headers=headers,
    )


# -- Handler registration -----------------------------------------------------

def register_exception_handlers(app: FastAPI) -> None:
    """Attach every exception handler to the FastAPI application."""

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        # Keep the error message in server logs for debugging; the client
        # receives the structured envelope only.
        logger.warning(
            "AppError request_id=%s code=%s status=%d message=%s",
            get_request_id(), exc.code, exc.status_code, exc.message,
        )
        return _error_response(
            exc.status_code, exc.code, exc.message, exc.details
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # pydantic validation errors -> 422 with per-field details
        details = [
            {
                "loc": ".".join(str(p) for p in err.get("loc", [])),
                "message": err.get("msg", "invalid value"),
                "type": err.get("type", "unknown"),
            }
            for err in exc.errors()
        ]
        return _error_response(422, "VALIDATION_ERROR", "Invalid request body", details)

    # Starlette's HTTPException (raised by the router for unmatched routes and
    # by raise_http_exception helpers) is a DIFFERENT class from FastAPI's
    # re-export, so register the custom handler for both.
    @app.exception_handler(HTTPException)
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        # Starlette / FastAPI built-in HTTP errors (e.g. 404 routes)
        message = exc.detail if isinstance(exc.detail, str) else "Request failed"
        return _error_response(exc.status_code, "HTTP_ERROR", message)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        # The full traceback stays in server logs; clients get a generic
        # message unless the app runs in debug mode.  This handler runs in
        # ServerErrorMiddleware, i.e. OUTSIDE the request-context middleware,
        # so the contextvar has already been reset: fall back to the IDs we
        # stashed on the ASGI scope.
        state = request.scope.get("state", {})
        request_id = get_request_id() or state.get("request_id", "")
        correlation_id = state.get("correlation_id", "")
        logger.exception(
            "Unhandled exception request_id=%s path=%s",
            request_id, request.url.path,
        )
        settings = get_settings()
        message = str(exc) if settings.debug else "Internal server error"
        headers = {}
        if request_id:
            headers["X-Request-ID"] = request_id
        if correlation_id:
            headers["X-Correlation-ID"] = correlation_id
        return _error_response(
            500, "INTERNAL_ERROR", message, headers=headers or None
        )