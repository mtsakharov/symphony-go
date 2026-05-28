"""Application configuration."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    app_name: str = "FastAPI Service"
    app_version: str = "1.0.0"
    environment: Literal["dev", "staging", "prod"] = "dev"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    api_v1_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/fastapi_service"
    media_storage_dir: Path = Path("var/media")
    media_public_url_prefix: str = "/media-files"
    media_max_size_bytes: int = 5 * 1024 * 1024
    media_allowed_content_types: tuple[str, ...] = (
        "image/gif",
        "image/jpeg",
        "image/png",
        "image/webp",
        "application/pdf",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""

    return Settings()
