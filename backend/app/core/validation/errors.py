"""Normalize Pydantic validation errors for the public API contract."""

from typing import Any

from fastapi.exceptions import RequestValidationError


def format_validation_errors(exc: RequestValidationError) -> list[dict[str, Any]]:
    """Return stable, client-friendly validation details."""

    return [
        {
            "field": ".".join(str(part) for part in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        }
        for error in exc.errors()
    ]
