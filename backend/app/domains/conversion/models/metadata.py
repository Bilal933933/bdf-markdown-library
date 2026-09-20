"""Document-level metadata — rich, never invented (Rule 1).

All fields optional with defaults; nothing here may be fabricated.
"""

from pydantic import BaseModel, Field, PositiveInt

from app.domains.conversion.models.enums import ExtractionMethod


class ContentStats(BaseModel):
    paragraphs: int = Field(default=0, ge=0)
    headings: int = Field(default=0, ge=0)
    tables: int = Field(default=0, ge=0)
    images: int = Field(default=0, ge=0)
    lists: int = Field(default=0, ge=0)
    quotes: int = Field(default=0, ge=0)
    code: int = Field(default=0, ge=0)


class ExtractionInfo(BaseModel):
    methods: list[ExtractionMethod] = Field(default_factory=list)
    ocr_pages: list[PositiveInt] = Field(default_factory=list)
    quality: float | None = Field(default=None, ge=0.0, le=1.0)


class DocumentMetadata(BaseModel):
    title: str | None = None
    subject: str | None = None
    grade: str | None = None
    stage: str | None = None
    page_count: int = Field(default=0, ge=0)
    stats: ContentStats = Field(default_factory=ContentStats)
    extraction: ExtractionInfo = Field(default_factory=ExtractionInfo)
