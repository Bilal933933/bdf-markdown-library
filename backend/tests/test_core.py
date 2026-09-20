import json
import logging
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import Settings, get_settings
from app.core.errors import (
    BadRequestError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
)
from app.core.errors import (
    ValidationError as AppValidationError,
)
from app.core.logging import configure_logging, request_id_var


class StorageSettings(Settings):
    storage_dir: Path = Path("storage")


def test_settings_factory_supports_extensions() -> None:
    get_settings.cache_clear()

    settings = get_settings(StorageSettings)

    assert isinstance(settings, StorageSettings)
    assert settings.storage_dir == Path("storage")
    assert get_settings(StorageSettings) is settings

    get_settings.cache_clear()


def test_production_debug_mode_is_rejected() -> None:
    with pytest.raises(ValidationError, match="DEBUG must be false"):
        Settings(app_env="production", debug=True)


@pytest.mark.parametrize("app_name", ["", "Invalid Name", "app_name", "-service"])
def test_invalid_app_name_is_rejected(app_name: str) -> None:
    with pytest.raises(ValidationError, match="APP_NAME"):
        Settings(app_name=app_name)


def test_app_name_is_normalized() -> None:
    settings = Settings(app_name="  My-Service  ")

    assert settings.app_name == "my-service"


def test_invalid_app_environment_is_rejected() -> None:
    with pytest.raises(ValidationError, match="app_env"):
        Settings(app_env="testing")


@pytest.mark.parametrize(
    ("error_type", "status_code", "code"),
    [
        (BadRequestError, 400, "BAD_REQUEST"),
        (UnauthorizedError, 401, "UNAUTHORIZED"),
        (ForbiddenError, 403, "FORBIDDEN"),
        (NotFoundError, 404, "NOT_FOUND"),
        (ConflictError, 409, "CONFLICT"),
        (AppValidationError, 422, "VALIDATION_ERROR"),
    ],
)
def test_expected_errors_have_stable_api_contract(
    error_type: type[Exception], status_code: int, code: str
) -> None:
    error = error_type()

    assert error.status_code == status_code  # type: ignore[attr-defined]
    assert error.code == code  # type: ignore[attr-defined]
    assert str(error)


def test_logging_writes_structured_json_with_request_id(tmp_path: Path) -> None:
    log_file = tmp_path / "app.log"
    configure_logging(log_file=log_file)
    token = request_id_var.set("request-123")
    try:
        logging.getLogger("tests.logging").info("conversion started")
    finally:
        request_id_var.reset(token)

    record = json.loads(log_file.read_text(encoding="utf-8").strip())
    assert record["event"] == "conversion started"
    assert record["request_id"] == "request-123"
    assert record["level"] == "info"
