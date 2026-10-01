"""OutputArtifact — one tracked file produced by a conversion.

Required: id, conversion_id, kind, key. Optional: sha256, size (0), mime.
"""

from pydantic import BaseModel, Field


class OutputArtifact(BaseModel):
    id: str
    conversion_id: str
    kind: str = "document"
    key: str
    sha256: str | None = None
    size: int = Field(default=0, ge=0)
    mime: str | None = None
