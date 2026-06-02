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
    chat_api_base_url: str = ""
    chat_api_posts_path: str = "/chat/posts"
    chat_api_timeout_seconds: float = 10.0
    chat_api_token: str | None = None
    chat_api_token_header: str = "Authorization"
    chat_api_forward_headers: str = "authorization,cookie,x-request-id"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""

    return Settings()
