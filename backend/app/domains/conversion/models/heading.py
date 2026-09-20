"""Heading payload. Required: level (1-6), text. Optional: none."""

from typing import Literal

from pydantic import BaseModel, Field


class HeadingPayload(BaseModel):
    kind: Literal["heading"] = "heading"
    level: int = Field(ge=1, le=6)
    text: str
