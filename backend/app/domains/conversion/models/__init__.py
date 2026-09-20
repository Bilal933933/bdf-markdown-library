"""Document Model schemas — one file per model; this package is the public API."""

from app.domains.conversion.models.asset import Asset
from app.domains.conversion.models.block import Block, BlockPayload
from app.domains.conversion.models.cell import Cell
from app.domains.conversion.models.checkpoint import PageCheckpoint
from app.domains.conversion.models.code import CodePayload
from app.domains.conversion.models.conversion import Conversion, ConversionError
from app.domains.conversion.models.document import Document
from app.domains.conversion.models.enums import (
    BlockType,
    CheckpointStatus,
    ConversionStatus,
    ExtractionMethod,
    UnitStatus,
)
from app.domains.conversion.models.heading import HeadingPayload
from app.domains.conversion.models.image import ImagePayload
from app.domains.conversion.models.list import ListItem, ListPayload
from app.domains.conversion.models.metadata import (
    ContentStats,
    DocumentMetadata,
    ExtractionInfo,
)
from app.domains.conversion.models.page import Page
from app.domains.conversion.models.paragraph import ParagraphPayload
from app.domains.conversion.models.quote import QuotePayload
from app.domains.conversion.models.row import Row
from app.domains.conversion.models.source import BBox, BlockSource
from app.domains.conversion.models.structure import Lesson, Section, Unit
from app.domains.conversion.models.table import TablePayload

__all__ = [
    "Asset",
    "BBox",
    "Block",
    "BlockPayload",
    "BlockSource",
    "BlockType",
    "Cell",
    "CheckpointStatus",
    "CodePayload",
    "ContentStats",
    "Conversion",
    "ConversionError",
    "ConversionStatus",
    "Document",
    "DocumentMetadata",
    "ExtractionInfo",
    "ExtractionMethod",
    "HeadingPayload",
    "ImagePayload",
    "Lesson",
    "ListItem",
    "ListPayload",
    "Page",
    "PageCheckpoint",
    "ParagraphPayload",
    "QuotePayload",
    "Row",
    "Section",
    "TablePayload",
    "Unit",
    "UnitStatus",
]
