"""Broker adapter registry: pluggable via BROKER_ADAPTER=angel_one|dhan|zerodha."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from app.core.config import settings

if TYPE_CHECKING:
    from app.adapters.broker.feed_base import HardenedFeedBase
    from app.adapters.broker.feed_manager import FeedManager


class BaseBrokerAdapter:
    """Base for broker adapters. Subclasses implement get_candles, get_option_chain and optional live feed."""

    def get_name(self) -> str:
        return "base"

    async def get_candles(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        return []

    async def get_option_chain(self, symbol: str) -> dict[str, Any]:
        return {"symbol": symbol, "strikes": [], "pcr": 1.0}

    async def connect(self) -> None:
        pass

    async def disconnect(self) -> None:
        pass

    def is_feed_fallback_active(self) -> bool:
        """True if hardened WebSocket feed is down/lagging and REST (get_candles) is the fallback."""
        try:
            from app.adapters.broker.feed_manager import get_feed_manager
            return get_feed_manager().is_fallback_active(self.get_name())
        except Exception:
            return True

    def get_feed_class(self) -> type["HardenedFeedBase"] | None:
        """Return hardened feed class for this adapter; None if no WebSocket feed."""
        return None


class BrokerAdapterRegistry:
    """Registry of broker adapters. Returns adapter by config key."""

    _adapters: dict[str, type] = {}

    @classmethod
    def register(cls, name: str):
        def deco(adapter_class: type):
            cls._adapters[name] = adapter_class
            return adapter_class
        return deco

    @classmethod
    def get_adapter(cls) -> BaseBrokerAdapter:
        key = getattr(settings, "broker_adapter", "angel_one") or "angel_one"
        adapter_class = cls._adapters.get(key, cls._adapters.get("angel_one"))
        if not adapter_class:
            return BaseBrokerAdapter()
        return adapter_class()
