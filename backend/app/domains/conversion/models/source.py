"""Provenance — where every block came from.

BBox: all fields required (x0, y0, x1, y1).
BlockSource required: file, pages, method. Optional: bbox, confidence, needs_review (False).
"""

from pydantic import BaseModel, Field, PositiveInt, model_validator

from app.domains.conversion.models.enums import ExtractionMethod


class BBox(BaseModel):
    x0: float
    y0: float
    x1: float
    y1: float

    @model_validator(mode="after")
    def check_corners(self) -> "BBox":
        if not (self.x1 > self.x0 and self.y1 > self.y0):
            raise ValueError("bbox requires x1 > x0 and y1 > y0")
        return self


class BlockSource(BaseModel):
    file: str
    pages: list[PositiveInt] = Field(min_length=1)
    bbox: BBox | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    method: ExtractionMethod
    needs_review: bool = False
