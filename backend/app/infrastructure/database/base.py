"""Declarative base for future ORM models — no tables in this slice.

Required: none. Optional: none (base only).
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
