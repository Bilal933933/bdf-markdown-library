"""File extraction public API — DOCX and plain text to Blocks."""

from app.domains.conversion.extract.docx import extract_docx
from app.domains.conversion.extract.text import decode_text, extract_text, split_paragraphs

__all__ = ["decode_text", "extract_docx", "extract_text", "split_paragraphs"]
