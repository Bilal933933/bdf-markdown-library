"""HTTP envelopes — the only API-level schemas.

Success: {"data": ..., "meta": {"request_id": ...}}.
Failure: {"error": {"code", "message", "details", "request_id"}}.
Domain truth lives in domains/*/models/, never here.
"""

from typing import Any

from pydantic import BaseModel


class Meta(BaseModel):
    request_id: str


class SuccessEnvelope[T](BaseModel):
    data: T
    meta: Meta


class ErrorBody(BaseModel):
    code: str
    message: str
    details: Any | None = None
    request_id: str


class ErrorEnvelope(BaseModel):
    error: ErrorBody
