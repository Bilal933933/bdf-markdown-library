"""ORM tables — persistence only; domain truth lives in domains/*/models/."""

import datetime

from sqlalchemy import DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class ConversionRow(Base):
    __tablename__ = "conversions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_file: Mapped[str] = mapped_column(String(1024))
    status: Mapped[str] = mapped_column(String(16), default="queued")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    total_pages: Mapped[int] = mapped_column(Integer, default=0)
    current_page: Mapped[int] = mapped_column(Integer, default=0)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True, default=None)
    error_message: Mapped[str | None] = mapped_column(String(2048), nullable=True, default=None)
    heartbeat_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class PageCheckpointRow(Base):
    __tablename__ = "page_checkpoints"

    conversion_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    page_number: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    method: Mapped[str | None] = mapped_column(String(16), nullable=True, default=None)
    quality: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
