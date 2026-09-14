from typing import Any
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class Settings(BaseSettings):
    # REASON: HTTP listening port of the microservice, defaults to 3001
    PORT: int = Field(default=3001, description="Listening port for Auth Service")

    # REASON: Database connection URL requiring postgresql+asyncpg driver
    DATABASE_URL: str = Field(
        ...,
        description="PostgreSQL auth_db connection URL using asyncpg driver"
    )

    # REASON: Redis connection URL for distributed rate limiting, loaded strictly from environment
    REDIS_URL: str = Field(
        ...,
        description="Redis connection URL including authentication (must be set in .env)"
    )

    # REASON: Secret key to sign and verify JWT tokens
    JWT_SECRET: str = Field(..., description="Secret key for JWT encryption")
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT encryption algorithm")

    # REASON: Short-lived Access Token (15 minutes) to minimize risk if token is leaked
    JWT_ACCESS_EXPIRES_IN_MINUTES: int = Field(default=15, description="Access token expiration in minutes (15 minutes)")

    # REASON: Long-lived Refresh Token (7 days) stored in DB to issue new access tokens
    JWT_REFRESH_EXPIRES_IN_DAYS: int = Field(default=7, description="Refresh token expiration in days (7 days)")
    JWT_EXPIRES_IN_MINUTES: int = Field(default=15, description="Backward-compatible alias for access token expiration")

    # REASON: Distributed Rate Limiting thresholds per endpoint
    RATE_LIMIT_LOGIN_MAX: int = Field(default=5, description="Maximum login requests allowed in window")
    RATE_LIMIT_LOGIN_WINDOW: int = Field(default=60, description="Login rate limit window in seconds")

    RATE_LIMIT_REGISTER_MAX: int = Field(default=3, description="Maximum registration requests allowed in window")
    RATE_LIMIT_REGISTER_WINDOW: int = Field(default=60, description="Registration rate limit window in seconds")

    RATE_LIMIT_REFRESH_MAX: int = Field(default=10, description="Maximum token refresh requests allowed in window")
    RATE_LIMIT_REFRESH_WINDOW: int = Field(default=60, description="Refresh rate limit window in seconds")

    # REASON: Allowed origins list for CORS, supports comma-separated string or JSON array
    CORS_ORIGINS: list[str] | str = Field(
        default_factory=list,
        description="List of origins allowed to make CORS requests"
    )

    @field_validator("CORS_ORIGINS", mode="after")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            v_stripped = v.strip()
            if not v_stripped:
                return []
            if v_stripped.startswith("[") and v_stripped.endswith("]"):
                import json
                return json.loads(v_stripped)
            return [origin.strip() for origin in v_stripped.split(",") if origin.strip()]
        elif isinstance(v, list):
            return v
        return []

    # REASON: Automatically load environment variables from .env file and ignore extra fields
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


# REASON: Initialize singleton settings instance for import across application
settings = Settings()
