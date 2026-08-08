"""
Application configuration.

All runtime configuration is loaded from environment variables via
pydantic-settings. This gives us validation at startup (the app refuses
to boot with missing/invalid config) instead of failing later at
first use, and gives every other module a single typed source of truth
instead of scattered os.environ calls.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings, populated from environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --- Application ---
    APP_NAME: str = "Enterprise AI Business Operations Platform"
    APP_ENV: str = Field(default="development")  # development | staging | production
    DEBUG: bool = Field(default=True)
    API_V1_PREFIX: str = "/api"

    # --- CORS ---
    CORS_ORIGINS: list[str] = Field(default=["http://localhost:3000"])

    # --- Database (wired in Module 2) ---
    DATABASE_URL: str = Field(
        default="postgresql+psycopg2://postgres:postgres@localhost:5432/enterprise_ai_platform"
    )
    # A SEPARATE database, used only by the test suite (see tests/conftest.py).
    # Tests create and drop every table each session — pointing this at the
    # same database as DATABASE_URL would silently wipe local dev / CI
    # runtime data every time `pytest` runs. Defaults to a sibling DB name
    # so `docker compose up` + `pytest` never collide by accident.
    TEST_DATABASE_URL: str = Field(
        default="postgresql+psycopg2://postgres:postgres@localhost:5432/enterprise_ai_platform_test"
    )

    # --- Auth (wired in Module 3) ---
    JWT_SECRET: str = Field(default="change-me-in-env-file")
    JWT_ALGORITHM: str = Field(default="HS256")
    JWT_EXPIRE_MINUTES: int = Field(default=60 * 24)

    # --- AI Providers (wired in later modules) ---
    GOOGLE_API_KEY: str = Field(default="")
    TAVILY_API_KEY: str = Field(default="")

    # --- Gmail (wired in Email Agent module) ---
    GMAIL_CLIENT_ID: str = Field(default="")
    GMAIL_CLIENT_SECRET: str = Field(default="")
    GMAIL_REFRESH_TOKEN: str = Field(default="")

    # --- Observability (wired in later modules) ---
    LANGSMITH_API_KEY: str = Field(default="")
    LANGSMITH_PROJECT: str = Field(default="enterprise-ai-platform")
    LANGCHAIN_TRACING_V2: bool = Field(default=False)


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor — settings are read once per process."""
    return Settings()