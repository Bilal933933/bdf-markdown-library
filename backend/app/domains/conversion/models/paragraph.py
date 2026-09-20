"""Paragraph payload. Required: text. Optional: none."""

from typing import Literal

from pydantic import BaseModel


class ParagraphPayload(BaseModel):
    kind: Literal["paragraph"] = "paragraph"
    text: str
