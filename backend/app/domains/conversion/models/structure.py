"""Educational structure — built by the Segmentation layer, not Extraction.

Section: all optional (heading_snapshot (""), block_refs ([])).
Lesson/Unit required: id. Optional: title (""), page_range, status (unknown_section),
confidence (0.0), sections/lessons ([]).
"""

from pydantic import BaseModel, Field, PositiveInt, model_validator

from app.domains.conversion.models.enums import UnitStatus


class Section(BaseModel):
    heading_snapshot: str = ""
    block_refs: list[str] = Field(default_factory=list)


class Lesson(BaseModel):
    id: str
    title: str = ""
    page_range: tuple[PositiveInt, PositiveInt] | None = None
    status: UnitStatus = UnitStatus.UNKNOWN_SECTION
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    sections: list[Section] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_page_range(self) -> "Lesson":
        if self.page_range is not None and self.page_range[1] < self.page_range[0]:
            raise ValueError("page_range end must be >= start")
        return self


class Unit(BaseModel):
    id: str
    title: str = ""
    page_range: tuple[PositiveInt, PositiveInt] | None = None
    status: UnitStatus = UnitStatus.UNKNOWN_SECTION
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    lessons: list[Lesson] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_page_range(self) -> "Unit":
        if self.page_range is not None and self.page_range[1] < self.page_range[0]:
            raise ValueError("page_range end must be >= start")
        return self
