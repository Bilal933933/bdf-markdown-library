"""Structured logging configuration for console and rotating file output."""

import logging
from collections.abc import Callable, MutableMapping
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

import structlog

from app.core.logging.context import get_request_id


def _add_request_id(
    _: Any, __: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    event_dict["request_id"] = get_request_id()
    return event_dict


def configure_logging(
    level: str = "INFO",
    *,
    log_file: Path = Path("logs/app.log"),
    max_bytes: int = 10_485_760,
    backup_count: int = 5,
) -> None:
    """Configure structured console logs and rotating JSON file logs."""

    log_file.parent.mkdir(parents=True, exist_ok=True)
    shared_processors: list[Callable[..., Any]] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        _add_request_id,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    structlog.configure(
        processors=[*shared_processors, structlog.processors.JSONRenderer()],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.JSONRenderer(),
        foreign_pre_chain=shared_processors,
    )
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    root = logging.getLogger()
    for handler in root.handlers[:]:
        handler.close()
    root.handlers.clear()
    root.addHandler(console_handler)
    root.addHandler(file_handler)
    root.setLevel(level)
