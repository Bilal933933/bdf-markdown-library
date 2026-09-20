"""List payload with nesting support.

ListItem required: text. Optional: level (0).
ListPayload required: items (min 1). Optional: ordered (False).
"""

from typing import Literal

from pydantic import BaseModel, Field


class ListItem(BaseModel):
    text: str
    level: int = Field(default=0, ge=0)


class ListPayload(BaseModel):
    kind: Literal["list"] = "list"
    ordered: bool = False
    items: list[ListItem] = Field(min_length=1)
