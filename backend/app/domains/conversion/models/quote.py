"""Quote payload. Required: text. Optional: attribution."""

from typing import Literal

from pydantic import BaseModel


class QuotePayload(BaseModel):
    kind: Literal["quote"] = "quote"
    text: str
    attribution: str | None = None
