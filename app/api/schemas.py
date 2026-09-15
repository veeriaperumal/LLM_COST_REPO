# ---------------------------------------------------------------------------
# schemas.py — Standard API response envelope
# ---------------------------------------------------------------------------
# Every business endpoint returns the same shape:
#
#   success: { "success": true,  "data": {...}, "error": null,
#              "meta": {"request_id": "...", "timestamp": "..."} }
#
#   error:   { "success": false, "data": null, "error": {"code": "...",
#              "message": "...", "details": null},
#              "meta": {"request_id": "...", "timestamp": "..."} }
#
# Health/probe endpoints intentionally stay raw for k8s / load-balancer
# conventions; this envelope applies to the API and error paths.
# ---------------------------------------------------------------------------

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel

from app.api.context import get_request_id


class ApiMeta(BaseModel):
    """Metadata attached to every API response."""

    request_id: str
    timestamp: str


class ApiError(BaseModel):
    """Structured error payload in the response envelope."""

    code: str
    message: str
    details: Any | None = None


class ApiResponse(BaseModel):
    """The standard envelope for all API responses."""

    success: bool
    data: Any | None = None
    error: ApiError | None = None
    meta: ApiMeta


def _meta() -> ApiMeta:
    """Build envelope metadata from the active request context."""
    return ApiMeta(
        request_id=get_request_id(),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def ok(data: Any | None = None) -> ApiResponse:
    """Build a success envelope."""
    return ApiResponse(success=True, data=data, error=None, meta=_meta())


def fail(
    code: str, message: str, details: Any | None = None
) -> ApiResponse:
    """Build an error envelope."""
    return ApiResponse(
        success=False,
        data=None,
        error=ApiError(code=code, message=message, details=details),
        meta=_meta(),
    )