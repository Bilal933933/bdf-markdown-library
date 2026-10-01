"""Conversion event log shapes — what the events card displays."""

import datetime

from pydantic import BaseModel, Field


class ConversionEvent(BaseModel):
    id: int
    kind: str
    request_id: str | None = None
    page_number: int | None = None
    method: str | None = None
    quality: float | None = Field(default=None, ge=0.0, le=1.0)
    note: str | None = None
    created_at: datetime.datetime | None = None
