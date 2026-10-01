"""ORM tables — persistence only; domain truth lives in domains/*/models/."""

import datetime

from sqlalchemy import DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class ConversionRow(Base):
    __tablename__ = "conversions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_file: Mapped[str] = mapped_column(String(1024))
    source_key: Mapped[str | None] = mapped_column(String(1024), nullable=True, default=None)
    source_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True, default=None)
    source_size: Mapped[int] = mapped_column(Integer, default=0)
    source_mime: Mapped[str | None] = mapped_column(String(128), nullable=True, default=None)
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
    note: Mapped[str | None] = mapped_column(String(512), nullable=True, default=None)


class ConversionEventRow(Base):
    __tablename__ = "conversion_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversion_id: Mapped[str] = mapped_column(String(64), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True, default=None)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    method: Mapped[str | None] = mapped_column(String(16), nullable=True, default=None)
    quality: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)
    note: Mapped[str | None] = mapped_column(String(512), nullable=True, default=None)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ArtifactRow(Base):
    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    conversion_id: Mapped[str] = mapped_column(String(64), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    key: Mapped[str] = mapped_column(String(1024), nullable=False)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True, default=None)
    size: Mapped[int] = mapped_column(Integer, default=0)
    mime: Mapped[str | None] = mapped_column(String(128), nullable=True, default=None)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
