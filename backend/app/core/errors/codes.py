"""Stable machine-readable codes returned by the API."""

from enum import StrEnum


class ErrorCode(StrEnum):
    APP_ERROR = "APP_ERROR"
    BAD_REQUEST = "BAD_REQUEST"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    HTTP_ERROR = "HTTP_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"
