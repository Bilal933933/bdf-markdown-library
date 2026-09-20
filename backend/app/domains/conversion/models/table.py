"""Table payload — rows of cells, no nesting in V1.

Required: rows (min 1). Optional: confidence, fallback_image.
"""

from typing import Literal

from pydantic import BaseModel, Field

from app.domains.conversion.models.row import Row


class TablePayload(BaseModel):
    kind: Literal["table"] = "table"
    rows: list[Row] = Field(min_length=1)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    fallback_image: str | None = None
