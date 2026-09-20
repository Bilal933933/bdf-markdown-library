"""Error envelope: every failure is {"error": {code, message, details, request_id}}."""

from typing import Any

from pydantic import BaseModel


class ErrorBody(BaseModel):
    code: str
    message: str
    details: Any | None = None
    request_id: str


class ErrorEnvelope(BaseModel):
    error: ErrorBody
