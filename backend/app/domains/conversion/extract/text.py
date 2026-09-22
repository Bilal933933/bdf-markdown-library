"""Plain-text extraction — blank-line paragraphs to Blocks (pure)."""

from app.domains.conversion.models import (
    Block,
    BlockSource,
    BlockType,
    ExtractionMethod,
    ParagraphPayload,
)


def split_paragraphs(text: str) -> list[str]:
    """Group lines into blank-line-separated chunks."""
    chunks: list[str] = []
    current: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            current.append(stripped)
        elif current:
            chunks.append(" ".join(current))
            current = []
    if current:
        chunks.append(" ".join(current))
    return chunks


def decode_text(data: bytes) -> str:
    """UTF-8 first, cp1256 fallback (decodes any byte sequence)."""
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("cp1256")


def extract_text(data: bytes, filename: str) -> list[Block]:
    text = decode_text(data)
    return [
        Block(
            id=f"p1-b{order}",
            type=BlockType.PARAGRAPH,
            order=order,
            source=BlockSource(file=filename, pages=[1], method=ExtractionMethod.TEXT),
            payload=ParagraphPayload(text=chunk),
        )
        for order, chunk in enumerate(split_paragraphs(text))
    ]
