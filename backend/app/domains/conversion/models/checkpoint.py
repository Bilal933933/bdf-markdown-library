"""PageCheckpoint — resume pointer of one page within a conversion.

Required: conversion_id, page_number. Optional: status (pending),
method, quality, attempts (0).
"""

from pydantic import BaseModel, Field, PositiveInt

from app.domains.conversion.models.enums import CheckpointStatus, ExtractionMethod


class PageCheckpoint(BaseModel):
    conversion_id: str
    page_number: PositiveInt
    status: CheckpointStatus = CheckpointStatus.PENDING
    method: ExtractionMethod | None = None
    quality: float | None = Field(default=None, ge=0.0, le=1.0)
    attempts: int = Field(default=0, ge=0)
