"""Application configuration."""

from functools import lru_cache
from typing import Literal

from pydantic import field_validator
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
    video_upload_allowed_mime_types: tuple[str, ...] = ("video/mp4",)
    video_upload_allowed_codecs: tuple[str, ...] = ("h264", "avc1")
    video_upload_max_size_bytes: int = 100_000_000
    video_upload_max_duration_seconds: int = 180
    video_upload_storage_prefix: str = "video-uploads"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator(
        "video_upload_allowed_mime_types",
        "video_upload_allowed_codecs",
        mode="before",
    )
    @classmethod
    def _normalize_csv_config(cls, value: object) -> object:
        """Accept comma-delimited or sequence values for list-like settings."""

        if isinstance(value, str):
            return tuple(item.strip().lower() for item in value.split(",") if item.strip())
        if isinstance(value, tuple | list | set):
            return tuple(str(item).strip().lower() for item in value if str(item).strip())
        return value


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""

    return Settings()
