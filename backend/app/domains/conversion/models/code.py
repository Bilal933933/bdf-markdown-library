"""Code payload. Required: text. Optional: language."""

from typing import Literal

from pydantic import BaseModel


class CodePayload(BaseModel):
    kind: Literal["code"] = "code"
    language: str | None = None
    text: str
