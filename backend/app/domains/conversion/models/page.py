"""Page — independent entity; resume and quality work at this level.

Required: number. Optional: width, height, blocks ([]), quality, extraction_method.
"""

from pydantic import BaseModel, Field, PositiveFloat, PositiveInt, model_validator

from app.domains.conversion.models.block import Block
from app.domains.conversion.models.enums import ExtractionMethod


class Page(BaseModel):
    number: PositiveInt
    width: PositiveFloat | None = None
    height: PositiveFloat | None = None
    blocks: list[Block] = Field(default_factory=list)
    quality: float | None = Field(default=None, ge=0.0, le=1.0)
    extraction_method: ExtractionMethod | None = None

    @model_validator(mode="after")
    def check_unique_orders(self) -> "Page":
        orders = [b.order for b in self.blocks]
        if len(set(orders)) != len(orders):
            raise ValueError("block orders must be unique within a page")
        ids = [b.id for b in self.blocks]
        if len(set(ids)) != len(ids):
            raise ValueError("block ids must be unique within a page")
        return self
