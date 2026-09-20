"""Reusable validation rules for application configuration."""

import re

APP_NAME_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,98}[a-z0-9])?$")


def validate_app_name(value: object) -> str:
    """Normalize and validate the public application name."""

    if not isinstance(value, str):
        raise TypeError("APP_NAME must be a string")

    normalized = value.strip().lower()
    if not normalized:
        raise ValueError("APP_NAME must not be empty")
    if len(normalized) > 100:
        raise ValueError("APP_NAME must be 100 characters or fewer")
    if not APP_NAME_PATTERN.fullmatch(normalized):
        raise ValueError("APP_NAME must contain only lowercase letters, numbers, and hyphens")

    return normalized


def validate_runtime_safety(app_env: str, debug: bool) -> None:
    """Reject unsafe combinations of runtime environment and debug mode."""

    if app_env == "production" and debug:
        raise ValueError("DEBUG must be false when APP_ENV is production")
