"""Request-ID middleware: one id per request, shared by logs and envelopes."""

import uuid
from typing import cast

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import request_id_var

REQUEST_ID_HEADER = "X-Request-ID"


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex[:12]
        token = request_id_var.set(request_id)
        try:
            response = cast(Response, await call_next(request))
        finally:
            request_id_var.reset(token)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response
