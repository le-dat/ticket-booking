from typing import Any
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PORT: int = Field(default=3004, description="Listening port for Payment Service")
    ENV: str = Field(default="development", description="Current environment (development, staging, production)")

    # Database & Cache
    DATABASE_URL: str = Field(
        ...,
        description="PostgreSQL payment_db connection URL using asyncpg driver",
    )
    REDIS_URL: str = Field(
        ...,
        description="Redis connection URL for idempotency and locks",
    )

    # Kafka Messaging
    KAFKA_BOOTSTRAP_SERVERS: str = Field(
        default="localhost:9092",
        description="Kafka broker bootstrap servers",
    )
    KAFKA_TOPIC_BOOKING_EVENTS: str = Field(
        default="booking-events",
        description="Kafka topic for booking events (BookingCreated, BookingCancelled)",
    )
    KAFKA_TOPIC_PAYMENT_EVENTS: str = Field(
        default="payment-events",
        description="Kafka topic for payment events (PaymentProcessed, PaymentExpired)",
    )
    KAFKA_CONSUMER_GROUP_ID: str = Field(
        default="payment-service-group",
        description="Kafka consumer group ID",
    )

    # Payment Gateway Configuration
    DEFAULT_PAYMENT_GATEWAY: str = Field(
        default="mock",
        description="Default payment gateway plugin (mock, vnpay, momo, stripe)",
    )
    WEBHOOK_SECRET: str = Field(
        ...,
        description="Shared secret key used to verify HMAC-SHA512 webhook signatures",
    )
    PAYMENT_RETURN_URL: str = Field(
        default="http://localhost:3000/booking/payment-result",
        description="Frontend redirect URL after customer completes payment",
    )

    # Stripe Gateway Configuration
    STRIPE_SECRET_KEY: str = Field(
        default="sk_test_mock_secret_key_ticket_booking",
        description="Stripe secret API key",
    )
    STRIPE_WEBHOOK_SECRET: str = Field(
        default="whsec_mock_webhook_secret_ticket_booking",
        description="Stripe webhook endpoint signing secret",
    )
    STRIPE_CURRENCY: str = Field(
        default="vnd",
        description="Stripe transaction currency",
    )

    # CORS
    CORS_ORIGINS: list[str] | str = Field(
        default_factory=list,
        description="List of origins allowed to make CORS requests",
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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
