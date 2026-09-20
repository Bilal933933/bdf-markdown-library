"""Image payload — references an Asset, never embeds bytes.

Required: asset_id. Optional: alt (""), caption.
"""

from typing import Literal

from pydantic import BaseModel


class ImagePayload(BaseModel):
    kind: Literal["image"] = "image"
    asset_id: str
    alt: str = ""
    caption: str | None = None
