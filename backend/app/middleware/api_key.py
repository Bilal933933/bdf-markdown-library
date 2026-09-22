"""API-key guard — everything under /api/v1 except /health needs X-API-Key.

Runs inside RequestIdMiddleware (added before it) so rejections carry the id.
No keys configured means open (local dev only).
"""

import secrets
from typing import cast

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.api.envelopes import ErrorBody, ErrorEnvelope
from app.core.config import get_settings
from app.core.errors.codes import ErrorCode
from app.core.logging import get_request_id

API_PREFIX = "/api/v1"
OPEN_PREFIXES = ("/api/v1/health",)


def is_open_path(path: str) -> bool:
    """Health subtree (probes) stays open."""
    return any(path == prefix or path.startswith(f"{prefix}/") for prefix in OPEN_PREFIXES)


API_KEY_HEADER = "X-API-Key"


def _configured_keys() -> dict[str, str]:
    """Map key -> role ('full' default, 'read' with a :read suffix)."""
    roles: dict[str, str] = {}
    for entry in get_settings().api_keys.split(","):
        name, _, role = entry.strip().partition(":")
        if name:
            roles[name] = "read" if role == "read" else "full"
    return roles


def _reject(status_code: int, code: ErrorCode, message: str) -> JSONResponse:
    envelope = ErrorEnvelope(
        error=ErrorBody(
            code=str(code),
            message=message,
            details=None,
            request_id=get_request_id(),
        )
    )
    return JSONResponse(status_code=status_code, content=jsonable_encoder(envelope))


class ApiKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        if not path.startswith(API_PREFIX) or is_open_path(path):
            return cast(Response, await call_next(request))
        keys = _configured_keys()
        if not keys:
            return cast(Response, await call_next(request))
        presented = request.headers.get(API_KEY_HEADER, "")
        if not presented:
            return _reject(401, ErrorCode.UNAUTHORIZED, "API key required")
        role: str | None = None
        for name, candidate_role in keys.items():
            if secrets.compare_digest(presented, name):
                role = candidate_role
                break
        if role is None:
            return _reject(403, ErrorCode.FORBIDDEN, "Invalid API key")
        if role == "read" and request.method not in ("GET", "HEAD", "OPTIONS"):
            return _reject(403, ErrorCode.FORBIDDEN, "Read-only API key")
        return cast(Response, await call_next(request))
