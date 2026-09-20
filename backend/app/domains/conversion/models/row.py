"""Row — ordered cells of one table row.

Required: cells (min 1). Optional: none.
"""

from pydantic import BaseModel, Field

from app.domains.conversion.models.cell import Cell


class Row(BaseModel):
    cells: list[Cell] = Field(min_length=1)
