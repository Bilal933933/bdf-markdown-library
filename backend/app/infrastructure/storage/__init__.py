"""Storage infrastructure public API."""

from app.infrastructure.storage.interface import Storage
from app.infrastructure.storage.local import LocalStorage

__all__ = ["LocalStorage", "Storage"]
