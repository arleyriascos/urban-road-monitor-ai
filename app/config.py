"""Service settings, read from environment variables or from a local .env file."""

from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration of the AI service.

    Each field is read from the environment variable with the same name in
    uppercase (for example, ``backend_url`` comes from ``BACKEND_URL``).
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: Literal["development", "production", "test"] = "development"
    """Environment where the service runs."""

    backend_url: str = "http://localhost:3000"
    """Base URL of the backend that serves the road graph."""

    internal_token: SecretStr | None = None
    """Shared token for the backend internal endpoints. Never logged or returned."""
