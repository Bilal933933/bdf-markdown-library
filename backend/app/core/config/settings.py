"""Application settings model and cached settings factory."""

from functools import cache
from pathlib import Path
from typing import Literal

from pydantic import PostgresDsn, RedisDsn, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.config.validators import validate_app_name, validate_runtime_safety

PROJECT_ROOT = Path(__file__).resolve().parents[4]
AppEnvironment = Literal["local", "staging", "production"]


class Settings(BaseSettings):
    """Base settings contract that application-specific settings can extend."""

    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", PROJECT_ROOT / "backend" / ".env"),
        env_ignore_empty=True,
        extra="ignore",
    )

    app_name: str = "document-conversion-engine"
    app_env: AppEnvironment = "local"
    debug: bool = True
    database_url: PostgresDsn | None = None
    redis_url: RedisDsn | None = None
    storage_dir: Path = PROJECT_ROOT / "storage"
    log_file: Path = PROJECT_ROOT / "logs" / "app.log"
    log_max_bytes: int = 10_485_760
    log_backup_count: int = 5

    @field_validator("app_name", mode="before")
    @classmethod
    def validate_name(cls, value: object) -> str:
        return validate_app_name(value)

    @model_validator(mode="after")
    def validate_runtime(self) -> "Settings":
        validate_runtime_safety(self.app_env, self.debug)
        return self


@cache
def get_settings(settings_type: type[Settings] = Settings) -> Settings:
    """Build and cache any settings contract derived from :class:`Settings`."""

    return settings_type()
