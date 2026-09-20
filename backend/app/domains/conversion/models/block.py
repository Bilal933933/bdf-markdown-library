"""Block — typed unit of content with a kind-discriminated payload.

Required: id, type, order, source, payload. Optional: none.
"""

from typing import Annotated

from pydantic import BaseModel, Field, model_validator

from app.domains.conversion.models.code import CodePayload
from app.domains.conversion.models.enums import BlockType
from app.domains.conversion.models.heading import HeadingPayload
from app.domains.conversion.models.image import ImagePayload
from app.domains.conversion.models.list import ListPayload
from app.domains.conversion.models.paragraph import ParagraphPayload
from app.domains.conversion.models.quote import QuotePayload
from app.domains.conversion.models.source import BlockSource
from app.domains.conversion.models.table import TablePayload

BlockPayload = Annotated[
    HeadingPayload
    | ParagraphPayload
    | ListPayload
    | TablePayload
    | ImagePayload
    | QuotePayload
    | CodePayload,
    Field(discriminator="kind"),
]


class Block(BaseModel):
    id: str
    type: BlockType
    order: int = Field(ge=0)
    source: BlockSource
    payload: BlockPayload

    @model_validator(mode="after")
    def check_payload_matches_type(self) -> "Block":
        if self.payload.kind != self.type.value:
            raise ValueError(
                f"payload kind {self.payload.kind!r} != block type {self.type.value!r}"
            )
        return self
