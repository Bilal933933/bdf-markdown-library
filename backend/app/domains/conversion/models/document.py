"""Document — root aggregate. Blocks are the source of truth.

Required: id, source_file. Optional: metadata, pages ([]), units ([]), assets ([]).
"""

from typing import Any

from pydantic import BaseModel, Field

from app.domains.conversion.models.asset import Asset
from app.domains.conversion.models.metadata import DocumentMetadata
from app.domains.conversion.models.page import Page
from app.domains.conversion.models.structure import Unit


class Document(BaseModel):
    id: str
    source_file: str
    metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)
    pages: list[Page] = Field(default_factory=list)
    units: list[Unit] = Field(default_factory=list)
    assets: list[Asset] = Field(default_factory=list)

    def model_post_init(self, __context: Any) -> None:
        if self.metadata.page_count == 0:
            self.metadata.page_count = len(self.pages)
