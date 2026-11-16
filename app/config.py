"""Service settings, read from environment variables or from a local .env file."""

from typing import Literal, Self
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

MIN_TOKEN_LENGTH = 32


class Settings(BaseSettings):
    """Configuration of the AI service.

    Each field is read from the environment variable with the same name in
    uppercase (for example, ``backend_url`` comes from ``BACKEND_URL``).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        # Validation errors must not repeat the input: it includes INTERNAL_TOKEN, and a
        # service that fails to start writes the error in the logs.
        hide_input_in_errors=True,
    )

    app_env: Literal["development", "production", "test"] = "development"
    """Environment where the service runs."""

    backend_url: str = "http://localhost:3000"
    """Base URL of the backend that serves the road graph, without a trailing slash."""

    internal_token: SecretStr | None = None
    """Shared token with the backend (at least 32 characters). Never logged or returned.

    It protects POST /routes and is sent to the backend to download the graph.
    Empty means not configured: POST /routes answers 404 and no graph is downloaded.
    """

    max_snap_distance_m: float = Field(default=200.0, gt=0, allow_inf_nan=False)
    """How far, in meters, a clicked point may be from the road network."""

    cluster_eps_m: float = Field(default=5.0, gt=0, le=1000, allow_inf_nan=False)
    """Detections closer than this many meters are taken as the same pothole."""

    cluster_min_points: int = Field(default=2, ge=1, le=100)
    """Detections needed, itself included, to confirm a pothole."""

    cluster_half_life_days: float = Field(default=30.0, gt=0, le=3650, allow_inf_nan=False)
    """Days after which a detection counts half as much for the confidence."""

    cluster_max_segment_distance_m: float = Field(default=25.0, gt=0, le=1000, allow_inf_nan=False)
    """How far from a street a pothole may be and still be placed on it."""

    cluster_max_detections: int = Field(default=20_000, ge=1, le=1_000_000)
    """The most detections one POST /clusters request may carry."""

    @field_validator("internal_token", mode="before")
    @classmethod
    def _empty_token_means_not_configured(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip()
            if value == "":
                return None
            if len(value) < MIN_TOKEN_LENGTH:
                raise ValueError(f"INTERNAL_TOKEN must have at least {MIN_TOKEN_LENGTH} characters")
        return value

    @field_validator("backend_url")
    @classmethod
    def _check_backend_url(cls, value: str) -> str:
        url = value.strip().rstrip("/")
        parts = urlsplit(url)
        if parts.scheme not in ("http", "https") or not parts.hostname:
            raise ValueError("BACKEND_URL must be an http:// or https:// address with a host")
        if parts.username or parts.password:
            raise ValueError("BACKEND_URL must not contain a user or a password")
        if parts.query or parts.fragment:
            raise ValueError("BACKEND_URL must not contain a query or a fragment")
        return url

    @model_validator(mode="after")
    def _require_https_in_production(self) -> Self:
        # Otherwise the token would travel in clear text to the backend.
        if self.app_env == "production" and urlsplit(self.backend_url).scheme != "https":
            raise ValueError("BACKEND_URL must use https:// when APP_ENV is production")
        return self
