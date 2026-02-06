"""
Application configuration via environment variables.
Uses pydantic-settings for validation and type safety.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """StrikeGenius.ai application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_name: str = "StrikeGenius.ai"
    debug: bool = False
    environment: Literal["development", "staging", "production"] = "development"

    # API
    api_v1_prefix: str = "/api/v1"
    openapi_url: str = "/openapi.json"

    # CORS (comma-separated origins in production, e.g. https://yourapp.vercel.app)
    cors_origins: str = Field(
        default="",
        description="Comma-separated allowed origins; empty = allow_origins from debug flag",
    )

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://strikegenius:strikegenius@localhost:5432/strikegenius"
    )
    database_url_sync: str = Field(
        default="postgresql://strikegenius:strikegenius@localhost:5432/strikegenius"
    )

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0")

    # JWT (set via SECRET_KEY or JWT_SECRET in env)
    secret_key: str = Field(default="change-me-in-production-use-hsm")
    jwt_secret: str | None = Field(default=None, description="Alias for secret_key; use JWT_SECRET in env")
    algorithm: str = "HS256"

    @model_validator(mode="after")
    def use_jwt_secret_if_set(self) -> "Settings":
        if self.jwt_secret:
            object.__setattr__(self, "secret_key", self.jwt_secret)
        return self
    access_token_expire_minutes: int = 60 * 24  # 24h

    # Billing (pluggable: set keys for Razorpay and/or Stripe)
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_webhook_secret: str = ""
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""

    # Broker adapter: angel_one | dhan | zerodha (pluggable)
    broker_adapter: str = "angel_one"
    angel_one_api_key: str = ""
    dhan_api_key: str = ""
    zerodha_api_key: str = ""

    # Market data pipeline (WebSocket hardening)
    feed_heartbeat_interval_sec: float = 30.0
    feed_lag_threshold_sec: float = 60.0
    feed_reconnect_max_retries: int = 10
    feed_reconnect_base_delay_sec: float = 1.0
    feed_reconnect_max_delay_sec: float = 120.0
    feed_token_refresh_before_expiry_sec: int = 300
    feed_fallback_enabled: bool = True

    # Limits (Free tier)
    free_scans_per_day: int = 5
    free_alerts_per_day: int = 5
    pro_scans_per_day: int = -1  # unlimited
    pro_alerts_per_day: int = -1


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()


settings = get_settings()
