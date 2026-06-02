"""Application configuration."""

from functools import lru_cache
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
    video_upload_allowed_mime_types: tuple[str, ...] = ("video/mp4",)
    video_upload_allowed_video_codecs: tuple[str, ...] = ("h264",)
    video_upload_allowed_audio_codecs: tuple[str, ...] = ("aac-lc",)
    video_upload_max_size_bytes: int = 262_144_000
    video_upload_max_duration_seconds: float = 120.0
    video_upload_storage_prefix: str = "video-post-uploads"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""

    return Settings()
