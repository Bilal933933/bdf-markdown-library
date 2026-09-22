"""Fixed-window rate limiting per identity (memory only, single process)."""

import time
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
from app.middleware.api_key import API_KEY_HEADER, API_PREFIX, is_open_path

WINDOW_SECONDS = 60.0

_hits: dict[str, list[float]] = {}


def reset_rate_limits() -> None:
    """Clear all counters (tests)."""
    _hits.clear()


def _identity(request: Request) -> str:
    if request.headers.get(API_KEY_HEADER):
        return f"key:{request.headers[API_KEY_HEADER]}"
    if request.client is not None:
        return f"ip:{request.client.host}"
    return "ip:unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if not request.url.path.startswith(API_PREFIX) or is_open_path(request.url.path):
            return cast(Response, await call_next(request))
        limit = get_settings().rate_limit_per_minute
        if limit <= 0:
            return cast(Response, await call_next(request))
        now = time.monotonic()
        identity = _identity(request)
        window = [hit for hit in _hits.get(identity, []) if now - hit < WINDOW_SECONDS]
        if len(window) >= limit:
            envelope = ErrorEnvelope(
                error=ErrorBody(
                    code=str(ErrorCode.RATE_LIMITED),
                    message="Rate limit exceeded",
                    details=None,
                    request_id=get_request_id(),
                )
            )
            return JSONResponse(status_code=429, content=jsonable_encoder(envelope))
        window.append(now)
        _hits[identity] = window
        return cast(Response, await call_next(request))
