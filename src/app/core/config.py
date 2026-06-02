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
    auth_jwt_secret: str = "development-secret-change-me"
    auth_jwt_algorithm: str = "HS256"
    auth_jwt_audience: str | None = None
    auth_jwt_issuer: str | None = None
    langgraph_api_url: str = "http://localhost:8080/qa"
    langgraph_timeout_seconds: float = 15.0
    langgraph_bearer_token: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator(
        "auth_jwt_audience",
        "auth_jwt_issuer",
        "langgraph_bearer_token",
        mode="before",
    )
    @classmethod
    def empty_strings_to_none(cls, value: str | None) -> str | None:
        """Normalize optional string settings loaded from empty env vars."""

        if value == "":
            return None
        return value


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""

    return Settings()
