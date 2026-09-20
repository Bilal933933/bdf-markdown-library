"""Cell — single table cell.

Required: none. Optional: text (""), header (False), colspan (1), rowspan (1).
An empty cell is valid data, hence every field has a default.
"""

from pydantic import BaseModel, PositiveInt


class Cell(BaseModel):
    text: str = ""
    header: bool = False
    colspan: PositiveInt = 1
    rowspan: PositiveInt = 1
