"""Asset — external file referenced by id, never embedded.

Required: id, storage_key, mime. Optional: kind ("image"), width, height, pages ([]).
"""

from typing import Literal

from pydantic import BaseModel, Field, PositiveFloat, PositiveInt


class Asset(BaseModel):
    id: str
    kind: Literal["image"] = "image"
    storage_key: str
    mime: str
    width: PositiveFloat | None = None
    height: PositiveFloat | None = None
    pages: list[PositiveInt] = Field(default_factory=list)
