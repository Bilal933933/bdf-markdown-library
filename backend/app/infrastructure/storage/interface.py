"""Storage contract — key to bytes only.

The storage layer knows nothing about Conversion, Document, or file types
(PDF, Markdown, image). It stores opaque bytes under opaque keys.
"""

from typing import Protocol


class Storage(Protocol):
    def save(self, key: str, data: bytes) -> str:
        """Store bytes under key; return the normalized key. Overwrites."""
        ...

    def load(self, key: str) -> bytes:
        """Return bytes for key; raise FileNotFoundError if missing."""
        ...

    def delete(self, key: str) -> None:
        """Remove key; missing keys are a no-op."""
        ...

    def exists(self, key: str) -> bool:
        """Return True iff key exists."""
        ...
