"""Conversion — root aggregate of the conversion domain.

Required: id, source_file. Optional: status (queued), progress (0),
total_pages (0), current_page (0), error.
"""

from pydantic import BaseModel, Field, model_validator

from app.domains.conversion.models.enums import ConversionStatus

_ALLOWED_TRANSITIONS: dict[ConversionStatus, set[ConversionStatus]] = {
    ConversionStatus.QUEUED: {ConversionStatus.PROCESSING},
    ConversionStatus.PROCESSING: {
        ConversionStatus.COMPLETED,
        ConversionStatus.FAILED,
        ConversionStatus.QUEUED,  # orphan recovery on worker startup (§27)
        ConversionStatus.PARTIAL,
    },
    ConversionStatus.FAILED: {ConversionStatus.QUEUED},
    ConversionStatus.PARTIAL: {ConversionStatus.QUEUED},
    ConversionStatus.COMPLETED: set(),
}


class ConversionError(BaseModel):
    code: str
    message: str


class Conversion(BaseModel):
    id: str
    source_file: str
    status: ConversionStatus = ConversionStatus.QUEUED
    progress: int = Field(default=0, ge=0, le=100)
    total_pages: int = Field(default=0, ge=0)
    current_page: int = Field(default=0, ge=0)
    error: ConversionError | None = None

    @model_validator(mode="after")
    def check_page_bounds(self) -> "Conversion":
        if self.current_page > self.total_pages:
            raise ValueError("current_page must be <= total_pages")
        return self

    def transition_to(self, target: ConversionStatus) -> "Conversion":
        """Return a copy in `target` status; reject illegal transitions."""
        if target not in _ALLOWED_TRANSITIONS[self.status]:
            raise ValueError(f"illegal transition {self.status.value} -> {target.value}")
        return self.model_copy(update={"status": target})
