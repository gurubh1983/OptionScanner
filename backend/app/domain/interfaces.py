"""
Domain interfaces (protocols). Adapters implement these.
Pluggable without code changes via config.
"""

from __future__ import annotations

from typing import Any, Protocol
import uuid
from datetime import datetime


class CandleRow:
    """Single OHLCV row."""
    __slots__ = ("ts", "open", "high", "low", "close", "volume")
    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class IMarketDataProvider(Protocol):
    """Provides OHLCV series from TimescaleDB or broker. Used by indicator/scanner."""

    async def get_candles(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 500,
        end_ts: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Return list of {ts, open, high, low, close, volume}."""
        ...

    async def get_option_chain_series(
        self,
        symbol: str,
        strike: float,
        expiry: str,
        option_type: str,
        timeframe: str,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        """OHLCV for a specific option contract. Optional."""
        ...


class IBrokerFeed(Protocol):
    """Live broker feed: Angel One, Dhan, Zerodha. Config selects one."""

    def get_name(self) -> str:
        ...

    async def get_candles(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        ...

    async def get_option_chain(self, symbol: str) -> dict[str, Any]:
        """PCR, strikes, OI, IV etc."""
        ...

    async def connect(self) -> None:
        ...

    async def disconnect(self) -> None:
        ...


class IPaymentGateway(Protocol):
    """Payment: Razorpay or Stripe. Config selects one per region."""

    def get_name(self) -> str:
        ...

    def create_subscription(
        self,
        user_id: str,
        plan_id: str,
        price_amount: int,
        currency: str,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        """Return {subscription_id, client_secret or payment_id}."""
        ...

    def verify_webhook(self, payload: bytes, signature: str) -> bool:
        ...

    def parse_webhook_event(self, payload: bytes) -> dict[str, Any]:
        """Return {event_type, subscription_id, status, ...}."""
        ...


class IUserRepository(Protocol):
    """User persistence."""

    async def get_by_id(self, user_id: uuid.UUID) -> Any | None:
        ...

    async def get_by_email(self, email: str) -> Any | None:
        ...

    async def create(self, email: str, hashed_password: str, full_name: str | None) -> Any:
        ...


class IPlanRepository(Protocol):
    """Plan lookup."""

    async def get_by_id(self, plan_id: str) -> Any | None:
        ...

    async def list_all(self) -> list[Any]:
        ...


class ISubscriptionRepository(Protocol):
    """Subscription CRUD and active lookup."""

    async def get_active_for_user(self, user_id: uuid.UUID) -> Any | None:
        ...

    async def upsert(
        self,
        user_id: uuid.UUID,
        plan_id: str,
        status: str,
        provider: str,
        provider_subscription_id: str | None,
        period_start: datetime | None,
        period_end: datetime | None,
        metadata: dict | None,
    ) -> Any:
        ...

    async def update_status(self, provider_subscription_id: str, status: str) -> None:
        ...


class IScanRepository(Protocol):
    """Scan run history for usage limits and replay."""

    async def count_scans_today(self, user_id: uuid.UUID) -> int:
        ...

    async def create(
        self,
        user_id: uuid.UUID | None,
        rule_id: uuid.UUID | None,
        rule_name: str,
        timeframe: str,
        result_count: int,
        duration_ms: int,
        result_snapshot: dict | None,
    ) -> Any:
        ...
